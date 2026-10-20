# Backend

FastAPI + Pydantic + SQLAlchemy + Alembic.

Owns all business logic, validation, and the API surface. PostgreSQL is the
system of record; this service is the only thing that talks to it directly.

**Status:** Phase 0, Step 0.2 complete — app skeleton, config, health
check, and Alembic wiring. No business tables or routes exist yet; those
start in Phase 1.

## Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app + CORS setup
│   ├── config/          # Pydantic settings (reads from environment/.env)
│   ├── database/        # SQLAlchemy engine, session, declarative Base
│   ├── api/              # Route modules (only /health exists so far)
│   ├── models/           # SQLAlchemy models 
│   ├── schemas/          # Pydantic request/response schemas 
│   ├── services/         # Business logic 
│   └── utils/             # Shared helpers 
├── alembic/               # Migration environment 
├── tests/                 # Backend unit tests
├── requirements.txt
├── .env.example
└── pytest.ini
```

## Setup

Requires Python 3.12+.

Using [`uv`](https://docs.astral.sh/uv/) (recommended):

```bash
cd backend
uv venv .venv --python 3.12
uv pip install -r requirements.txt
```

Or with plain `venv` + `pip`:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy the environment template and adjust if needed (defaults work for
local dev without any changes — the database isn't used yet):

```bash
cp .env.example .env
```

## Running the API

```bash
.venv/bin/uvicorn app.main:app --reload
```

Then check:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

Interactive API docs: http://127.0.0.1:8000/docs

## Running tests

```bash
.venv/bin/pytest -v
```

## Database migrations (Alembic)

Alembic is configured (`alembic/env.py` reads the DB URL from app settings
— nothing is hardcoded), but **no migrations exist yet** since there are no
models. Once Phase 1 adds models under `app/models/`, generate the first
migration with:

```bash
.venv/bin/alembic revision --autogenerate -m "create initial tables"
.venv/bin/alembic upgrade head
```

This requires a running PostgreSQL instance matching `DATABASE_URL` in
`.env` — not needed for Phase 0.

## Notes

- No Docker, Celery, or message brokers are used at this stage — kept
  deliberately simple per the Phase 0 scope.
- CORS is configured via `CORS_ORIGINS` in `.env` (comma-separated), so the
  Next.js frontend can call this API in development without code changes.
