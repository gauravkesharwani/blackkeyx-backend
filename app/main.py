import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.db.session import init_db
from app.middleware.rate_limit import limiter

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    await init_db()

    # Start callback scheduler
    scheduler_task = None
    if settings.callback_scheduler_enabled:
        from app.services.callback_scheduler import get_callback_scheduler

        scheduler = get_callback_scheduler()
        scheduler_task = asyncio.create_task(scheduler.run())

    # Start voicemail retry scheduler
    voicemail_task = None
    if settings.voicemail_detection_enabled:
        from app.services.voicemail_scheduler import get_voicemail_scheduler

        vm_scheduler = get_voicemail_scheduler()
        voicemail_task = asyncio.create_task(vm_scheduler.run())

    yield

    # Shutdown
    if voicemail_task:
        from app.services.voicemail_scheduler import get_voicemail_scheduler

        get_voicemail_scheduler().stop()
        try:
            await asyncio.wait_for(voicemail_task, timeout=10.0)
        except asyncio.TimeoutError:
            voicemail_task.cancel()

    if scheduler_task:
        from app.services.callback_scheduler import get_callback_scheduler

        get_callback_scheduler().stop()
        try:
            await asyncio.wait_for(scheduler_task, timeout=10.0)
        except asyncio.TimeoutError:
            scheduler_task.cancel()


app = FastAPI(
    title="BlackKeyX API",
    description="Autonomous Capital Alignment System - Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Import and include routers
from app.routers import admin, leads, matching, properties, voice, webhook  # noqa: E402

app.include_router(leads.router, prefix="/api/v1", tags=["leads"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(properties.router, prefix="/api/v1/properties", tags=["properties"])
app.include_router(voice.router, tags=["voice"])
app.include_router(matching.router, tags=["matching"])
app.include_router(webhook.router, tags=["voice-webhook"])
