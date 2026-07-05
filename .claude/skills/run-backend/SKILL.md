---
name: run-backend
description: Use when launching, restarting, or checking the FastAPI backend for this project. Triggers on "chạy BE", "chạy backend", "start backend", "khởi động lại BE", "build BE", or any /run invocation targeting the API server.
---

# Run Backend

## Overview

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL. No build/compile step — Python runs from source. To pick up code changes, either run with `--reload` (auto) or restart the process manually.

## Setup (one-time)

```bash
# Dependencies (already in .venv if it exists — check first)
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt

# Env file (copy once, then edit secrets)
cp .env.example .env
```

## Database — 2 options

| Option | When to use | DATABASE_URL |
|--------|-------------|---------------|
| **PostgreSQL** (default, `.env`) | Full parity with production | `postgresql+asyncpg://pos_user:pos_secret@localhost:5432/pos_db` (already in `.env.example`) |
| **SQLite `dev.db`** | Quick local/mobile testing, no Docker needed | `sqlite+aiosqlite:///./dev.db` (override via env var, don't edit `.env`) |

### PostgreSQL path

```bash
docker compose up -d db          # starts Postgres on :5432
.venv/Scripts/python.exe -m alembic upgrade head   # apply migrations
```

### SQLite path (matches the DB the Android app dev build uses)

```bash
# Seed fresh data into ./dev.db (idempotent-ish; re-run to reset)
.venv/Scripts/python.exe scripts/seed_sqlite.py
```

Seeds: 1 tenant + 2 users, categories, 10 suppliers, 100 products, 30 customers, opening stock + kardex.

**Login after seeding:**
- OWNER: `0901234567` / `owner123`
- CASHIER: `0912345678` / `cashier123`

## Run the server

```bash
# Postgres (uses .env's DATABASE_URL)
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# SQLite dev.db (override DATABASE_URL for this run only)
DATABASE_URL="sqlite+aiosqlite:///./dev.db" .venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` watches source files and restarts automatically on save — no manual restart needed while it's running. Open `http://localhost:8000/docs` for interactive API docs.

**Port 8000 already in use?** Something else (often a dev server started earlier in the session, or your own terminal) is already serving the backend — check `http://localhost:8000/docs` before starting a second instance; killing/restarting an existing `--reload` process is unnecessary since it already picked up your changes.

## Tests

```bash
.venv/Scripts/python.exe -m pytest              # full suite
.venv/Scripts/python.exe -m pytest tests/test_product.py -v   # one file
.venv/Scripts/python.exe -m pytest -k stock_status -v         # by keyword
```

Tests spin up their own isolated DB session per test (see `tests/conftest.py`) — no need for the dev server or seeded data to be running.

## When you DON'T need a restart

Pydantic schema field additions, new endpoints, service-layer logic changes — all picked up automatically by `--reload`, or by starting fresh if not using `--reload`. No DB migration needed unless you added/changed a SQLAlchemy **model** (column/table) — those require a new Alembic revision:

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "description"
.venv/Scripts/python.exe -m alembic upgrade head
```
