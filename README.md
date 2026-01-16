# BlackKeyX Backend

Autonomous Capital Alignment System Backend API built with FastAPI.

## Setup

```bash
uv venv
uv pip install -e .
source .venv/bin/activate
```

## Run

```bash
uvicorn app.main:app --reload
```

## Database Migrations

```bash
alembic upgrade head
```
