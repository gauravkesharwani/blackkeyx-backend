# Callback Scheduler Implementation Plan

## Context

When an investor requests a callback during a call, the system creates a `CallbackRequest` record — but never auto-dispatches the follow-up. The original plan covered the scheduler loop but had **5 shortcomings** that this revised plan addresses:

1. **No timezone handling** — `dateparser.parse("2pm")` returns naive datetime assumed as UTC. An investor in PST saying "call me at 2pm" gets called at 2pm UTC (7am PST) instead of 2pm PST (10pm UTC).
2. **`get_pending_callbacks()` doesn't filter by due time** — returns ALL pending callbacks, not just those whose `requested_datetime` is due.
3. **No DB session management** — the scheduler runs outside FastAPI request context and needs its own sessions via `async_session_factory`.
4. **No transaction commits** — the original plan omits `session.commit()`.
5. **Inconsistent `datetime.utcnow()`** — naive datetimes in `call_repo.py` despite `DateTime(timezone=True)` columns.

---

## Timezone Strategy

**Primary:** The voice agent confirms the investor's timezone during the call. It's passed back via a new `investor_timezone` field on the `SessionCompleteRequest` and saved to `InvestorProfile.timezone`.

**Fallback:** If the call didn't capture timezone (field is null), infer it from the investor's phone number area code using the `phonenumbers` library.

**Last resort:** Default to `America/New_York`.

### Agent-side changes (blackkeyx-agent)

The voice agent must be updated to capture timezone and pass it to the backend. Three changes in `agent.py`:

#### A. Add `investor_timezone` parameter to `request_callback` tool

Add an `investor_timezone` parameter to the `request_callback` function tool (line 230) so the LLM can pass the investor's timezone when scheduling a callback:

```python
@function_tool()
async def request_callback(
    self,
    ctx: RunContext,
    callback_datetime: str,
    callback_notes: str = "",
    investor_timezone: str = "",
) -> str:
    """
    Called when the user indicates they're busy and wants a callback at a specific time.

    Args:
        callback_datetime: The preferred callback date/time in natural language
                          (e.g., "Tuesday at 2pm", "tomorrow morning", "next week")
        callback_notes: Optional notes about the callback
        investor_timezone: The investor's timezone as confirmed during the call
                          (e.g., "Eastern", "Pacific", "Central", "Mountain").
                          Ask the investor to confirm their timezone before calling this tool.
    """
```

Store `investor_timezone` alongside the other callback fields in `_callback_requests`:

```python
_callback_requests[job_ctx.room.name] = {
    "callback_datetime": callback_datetime,
    "callback_notes": callback_notes,
    "investor_timezone": investor_timezone,
}
```

#### B. Include `investor_timezone` in the session-complete payload

In `send_transcript()` (line 313), pass the timezone when building the payload:

```python
if callback_info:
    payload["callback_requested"] = True
    payload["callback_datetime"] = callback_info["callback_datetime"]
    payload["callback_notes"] = callback_info.get("callback_notes", "")
    payload["investor_timezone"] = callback_info.get("investor_timezone", "")
```

#### C. Update agent instructions to ask for timezone

In the outbound call flow instructions (line 128-131), after the "bad time" branch where the agent asks when to call back, add a step to confirm timezone:

```text
- If they CONFIRM but say it is a BAD TIME:
  1. Acknowledge politely (e.g., "I completely understand, I know you're busy")
  2. Ask when would be a good time to call back
  3. Confirm their timezone (e.g., "And just to make sure we call at the right time — are you on Eastern time?")
  4. Once they give a time and timezone, use the request_callback tool with their preferred time and timezone
```

**Why the agent must ask:** The backend plan relies on `investor_timezone` being passed from the agent callback. Without this prompt change, the LLM will never ask for timezone and the field will always be empty, falling through to phone-number inference every time.

---

## Files to Change

| File | Action | Purpose |
|------|--------|---------|
| `blackkeyx-agent/agent.py` | Modify | Add `investor_timezone` to `request_callback` tool, payload, and instructions |
| `app/models/investor.py` | Modify | Add `timezone` field |
| `alembic/versions/012_add_investor_timezone.py` | Create | Migration for timezone column |
| `app/utils/__init__.py` | Create | New utils package |
| `app/utils/timezone.py` | Create | Phone-to-timezone inference |
| `app/routers/voice.py` | Modify | Add `investor_timezone` to `SessionCompleteRequest` |
| `app/services/voice_service.py` | Modify | Save timezone from call, fix dateparser |
| `app/db/repositories/call_repo.py` | Modify | Add `get_due_callbacks()`, fix naive datetimes |
| `app/services/callback_scheduler.py` | Create | Core scheduler service |
| `app/config.py` | Modify | Add 4 scheduler settings |
| `app/main.py` | Modify | Start/stop scheduler in lifespan |
| `requirements.txt` | Modify | Add `phonenumbers` |
| `pyproject.toml` | Modify | Add `phonenumbers` |

---

## Step 1: Add `timezone` field to InvestorProfile

**File:** `app/models/investor.py` — add after `name` field (line 51):

```python
timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

Nullable IANA timezone string (e.g. `"America/New_York"`). Populated from the call when the voice agent confirms the investor's timezone. Existing rows get NULL; the system falls back to phone-number inference.

**Migration:** `alembic/versions/012_add_investor_timezone.py`
- Revises: `011_add_vector_indexes`
- `upgrade()`: `op.add_column("investor_profiles", sa.Column("timezone", sa.String(50), nullable=True))`
- `downgrade()`: `op.drop_column("investor_profiles", "timezone")`

---

## Step 2: Create timezone utility

**File:** `app/utils/timezone.py` (new — also create `app/utils/__init__.py`)

Two functions:

- **`infer_timezone_from_phone(phone: str) -> Optional[str]`** — Uses `phonenumbers` library to map E.164 phone to IANA timezone via area code. e.g. `+1415...` → `America/Los_Angeles`.
- **`get_investor_timezone(explicit_tz, phone) -> str`** — Priority chain: (1) explicit `timezone` field from profile (confirmed during call) if valid, (2) phone inference, (3) fallback `"America/New_York"`.

**Dependency:** Add `phonenumbers` to `requirements.txt` and `pyproject.toml`.

---

## Step 3: Capture timezone from call & fix datetime parsing

### 3a. Add `investor_timezone` to SessionCompleteRequest

**File:** `app/routers/voice.py` — add to `SessionCompleteRequest` (line 44):

```python
investor_timezone: Optional[str] = None  # IANA timezone confirmed during call
```

Pass it through to `voice_service.complete_session()` in the endpoint handler (~line 98).

### 3b. Save timezone and use it for parsing

**File:** `app/services/voice_service.py` — modify `complete_session()`:

1. Add `investor_timezone: Optional[str] = None` parameter
2. If `investor_timezone` is provided, save it to the investor profile:

   ```python
   if investor_timezone:
       investor = await self.investor_repo.get(call.investor_id)
       if investor:
           investor.timezone = investor_timezone
           await self.session.flush()
   ```

3. Replace the dateparser call (~line 88):

Before:

```python
parsed_dt = dateparser.parse(callback_datetime, settings={"PREFER_DATES_FROM": "future"})
```

After:

```python
investor = await self.investor_repo.get(call.investor_id)
investor_tz = get_investor_timezone(
    getattr(investor, 'timezone', None),
    investor.phone if investor else None,
)
parsed_dt = dateparser.parse(callback_datetime, settings={
    "PREFER_DATES_FROM": "future",
    "TIMEZONE": investor_tz,
    "RETURN_AS_TIMEZONE_AWARE": True,
    "TO_TIMEZONE": "UTC",
})
```

This ensures "2pm" for a PST investor is stored as 10pm UTC. The timezone saved from the call (step 3b.2) takes priority over phone inference.

---

## Step 4: Add `get_due_callbacks()` to CallRepository

**File:** `app/db/repositories/call_repo.py` — add new method after `get_pending_callbacks` (line 169):

```python
async def get_due_callbacks(self, grace_window_minutes: int = 2) -> Sequence[CallbackRequest]:
    cutoff = datetime.now(timezone.utc) + timedelta(minutes=grace_window_minutes)
    query = (
        select(CallbackRequest)
        .where(CallbackRequest.status == "pending")
        .where(CallbackRequest.requested_datetime.isnot(None))
        .where(CallbackRequest.requested_datetime <= cutoff)
        .order_by(CallbackRequest.requested_datetime.asc())
    )
    result = await self.session.execute(query)
    return result.scalars().all()
```

Also fix `datetime.utcnow()` → `datetime.now(timezone.utc)` at lines 53 and 96.

**Why a new method:** Existing `get_pending_callbacks()` is used by `admin_service.py` to find ALL pending callbacks for a specific investor. Adding time filtering there would break that flow.

---

## Step 5: Add config settings

**File:** `app/config.py` — add after `cors_origins` (line 49):

```python
# Callback Scheduler
callback_scheduler_enabled: bool = True
callback_poll_interval_seconds: int = 30
callback_grace_window_minutes: int = 2
callback_max_retries: int = 3
```

All configurable via env vars (e.g. `CALLBACK_SCHEDULER_ENABLED=false`).

---

## Step 6: Create callback scheduler service

**File:** `app/services/callback_scheduler.py` (new)

Class `CallbackScheduler` with:

- **`run()`** — async loop polling every `poll_interval` seconds. Sleeps in 1-second increments so `stop()` takes effect quickly.
- **`_poll_and_dispatch()`** — creates its own `async_session_factory()` session (same pattern as background tasks in `voice_service.py`). Queries `get_due_callbacks()`, dispatches each, commits, handles rollback on error.
- **`_dispatch_callback()`** — replicates `admin_service.py:104-135`:
  1. Load investor via `InvestorRepository.get()`
  2. Cancel callback if investor missing or no phone
  3. Build `investor_context` dict with `is_callback=True`
  4. Call `LiveKitDispatcher.dispatch_outbound_call()` with retry
  5. Create `CallSession` via `CallRepository.create_call()`
  6. Update stage to `call_dispatched` via `InvestorRepository.update_stage(changed_by="callback_scheduler")`
  7. Mark callback `completed` via `CallRepository.update_callback_status()`
- **`_dispatch_with_retry()`** — exponential backoff (2s, 4s, 8s). If all retries fail, callback stays `pending` for next cycle.
- **Duplicate prevention** — in-memory `_dispatching: Set[UUID]` tracks in-flight callback IDs.
- **Singleton** — `get_callback_scheduler()` function.

**DB sessions:** Each poll cycle uses `async with async_session_factory() as session`, commits after all dispatches in the cycle, rolls back on error.

---

## Step 7: Integrate with FastAPI lifespan

**File:** `app/main.py` — modify lifespan (lines 17-24):

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()

    scheduler_task = None
    if settings.callback_scheduler_enabled:
        from app.services.callback_scheduler import get_callback_scheduler
        scheduler = get_callback_scheduler()
        scheduler_task = asyncio.create_task(scheduler.run())

    yield

    if scheduler_task:
        get_callback_scheduler().stop()
        try:
            await asyncio.wait_for(scheduler_task, timeout=10.0)
        except asyncio.TimeoutError:
            scheduler_task.cancel()
```

---

## Edge Cases

| Case | Behavior |
|------|----------|
| `requested_datetime` is NULL | Skipped by `get_due_callbacks` (filtered out) |
| LiveKit dispatch fails | Retry up to `max_retries` with exponential backoff, leave `pending` on exhaustion |
| Investor not found / no phone | Mark callback `cancelled` |
| Duplicate dispatch (slow dispatch + next poll) | In-memory `_dispatching` set prevents double-dispatch |
| DB session error | Rollback + retry on next cycle |
| Invalid timezone on profile | Falls back to phone inference, then `America/New_York` |

---

## Verification

1. `pip install phonenumbers` and start backend with `CALLBACK_SCHEDULER_ENABLED=true`
2. Submit a lead via `/api/v1/submit-lead` — initial call dispatches
3. When LiveKit agent posts to `/api/v1/voice/session-complete` with `callback_requested=true`, `callback_datetime="in 2 minutes"`, and `investor_timezone="America/Los_Angeles"`, verify `callback_requests.requested_datetime` is stored as UTC-aware datetime
4. Watch logs — within ~30s of the requested time, scheduler logs dispatch
5. Verify `callback_requests.status = "completed"` and investor `stage = "call_dispatched"` in DB
6. Test timezone: create a callback with `callback_datetime="at 2pm"` for an investor with a West Coast phone number (+1415...). Verify `requested_datetime` is stored as 10pm UTC (PST offset), not 2pm UTC
