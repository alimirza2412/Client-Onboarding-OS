# Client Onboarding OS

AI-powered Client Onboarding OS. Turns a signed/accepted client into a
delivery-ready client automatically. Initial vertical: Agencies. Future
verticals: Consulting, Recruiting, Legal — built on the same core engine.

## Status

**Working 2-day demo** — Phases 0 through 13 implemented and verified
end-to-end (real PostgreSQL with Row-Level Security, real Temporal
workflow engine, real FastAPI backend, real Next.js frontend). Phase 14
(production deployment) is out of scope for a demo.

See `DEMO_SETUP.md` for exact setup/run/test commands and
`CHANGELOG.md` for what was implemented and what was deliberately
simplified for demo purposes.

## Quick start

```bash
# See DEMO_SETUP.md for full details — this is the short version,
# assuming PostgreSQL and Temporal are already installed and running.
cd backend && uv pip install -r requirements.txt && .venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload &          # terminal 1
.venv/bin/python -m app.worker &                    # terminal 2
cd ../frontend && npm install && npm run dev &      # terminal 3
cd ../backend && .venv/bin/python scripts/seed_demo.py   # walks the full flow end-to-end
```

## Structure

- `frontend/` — Next.js + TypeScript + Tailwind + shadcn/ui (login,
  dashboard, clients, forms, templates, onboarding instances, client
  portal)
- `backend/` — FastAPI + Pydantic + SQLAlchemy + Alembic + Temporal
  worker (`app/worker.py`) — auth/RBAC, clients, forms, documents,
  onboarding workflow, dashboard
- `infrastructure/` — (no containerized services for the demo — see
  DEMO_SETUP.md for running Postgres/Temporal directly)
- `docs/` — Architecture, roadmap, research, and decisions log
- `tests/` — (backend tests live in `backend/tests/` — see
  DEMO_SETUP.md)

## Core principles

- PostgreSQL is the system of record.
- Temporal owns durable workflow execution (retries, waits, human approvals,
  crash recovery).
- Redis handles cache / temporary operations only — not used in this
  demo build (see CHANGELOG.md); the architecture reserves it for later.
- AI (Groq) assists — classification, extraction, summarization, drafting —
  but never owns critical workflow state.
- Every tenant-owned table has `organization_id`; isolation is enforced by
  both application-level filters and PostgreSQL Row-Level Security.
- One core onboarding engine; verticals are templates/config on top of it,
  not separate systems.

See `docs/decisions.md` for finalized implementation decisions and
`docs/roadmap.md` for the full phase-by-phase build plan.
