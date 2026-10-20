# DEMO_SETUP.md

Exact commands to install, configure, run, and test the Client Onboarding
OS demo. Written for Ubuntu/Debian (including WSL2) — commands are
standard enough to adapt to macOS easily (use `brew` instead of `apt`).

This is a **2-day demo/prototype**, not a production build. See
`CHANGELOG.md` for what's implemented and what's deliberately simplified.

---

## 0. What you need running, at a glance

Five things run at once during the demo, each in its own terminal:

1. PostgreSQL (background service)
2. Temporal dev server (background service)
3. FastAPI backend (`uvicorn`)
4. Temporal worker (`python -m app.worker`)
5. Next.js frontend (`npm run dev`)

---

## 1. Prerequisites

```bash
python3 --version   # need 3.12+
node --version       # need 20+
npm --version
```

If you don't have `uv` (faster pip, recommended but optional):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Install and start PostgreSQL

One command does everything below (install if needed, start it, create
the database, create both roles, set grants):

```bash
./infrastructure/setup_db.sh
```

Safe to re-run any time. See `infrastructure/README.md` for details.
Passwords default to match `backend/.env.example` — no other changes
needed to use it as-is.

<details>
<summary>Prefer to do it by hand instead? (exactly what the script above does)</summary>

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo pg_ctlcluster 16 main start   # or: sudo service postgresql start
```

Create the database and the two roles the app needs — **read
`docs/decisions.md` (decision D2) for why there are two roles**: an
owner role for migrations, and a separate non-owner role for the running
app, so PostgreSQL Row-Level Security actually applies to it.

```bash
sudo -u postgres psql <<'EOF'
CREATE DATABASE onboarding_os;

CREATE ROLE onboarding_owner WITH LOGIN PASSWORD 'onboarding_owner_pw' CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE onboarding_os TO onboarding_owner;

CREATE ROLE onboarding_app WITH LOGIN PASSWORD 'onboarding_app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE onboarding_os TO onboarding_app;
EOF

sudo -u postgres psql -d onboarding_os <<'EOF'
GRANT USAGE ON SCHEMA public TO onboarding_app;
GRANT USAGE, CREATE ON SCHEMA public TO onboarding_owner;
ALTER DEFAULT PRIVILEGES FOR ROLE onboarding_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO onboarding_app;
EOF
```
</details>
```

Passwords above match the defaults in `backend/.env.example` — change
both if you want different credentials (keep them in sync).

---

## 3. Install and start Temporal (dev server)

No Docker needed — Temporal ships a single self-contained binary for
local development.

```bash
curl -sL "https://github.com/temporalio/cli/releases/download/v1.8.2/temporal_cli_1.8.2_linux_amd64.tar.gz" -o /tmp/temporal_cli.tar.gz
mkdir -p /tmp/temporal-cli && tar -xzf /tmp/temporal_cli.tar.gz -C /tmp/temporal-cli
sudo cp /tmp/temporal-cli/temporal /usr/local/bin/temporal
temporal --version
```

Start it (leave this running in its own terminal):

```bash
temporal server start-dev --db-filename /tmp/temporal-cli/temporal.db
```

- Temporal UI: http://localhost:8080 (useful during the demo — you can
  watch workflow executions live)
- gRPC endpoint: `127.0.0.1:7233` (what the app connects to)

---

## 4. Backend setup

```bash
cd backend
uv venv .venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
```

The defaults in `.env` match steps 2–3 above and work with no edits,
**except** `GROQ_API_KEY`, which is optional — see § 9.

Run migrations (creates all tables, enables Row-Level Security, and
creates the two `SECURITY DEFINER` helper functions described in
`docs/decisions.md`):

```bash
.venv/bin/alembic upgrade head
```

Start the API (own terminal):
```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the Temporal worker (**separate terminal** — this is a distinct
long-running process from the API):
```bash
cd backend
.venv/bin/python -m app.worker
```

Verify:
```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

---

## 5. Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Visit http://localhost:3000.

---

## 6. Seed demo data + verify the whole flow at once

With all five services running, from `backend/`:

```bash
.venv/bin/python scripts/seed_demo.py
```

This registers a demo agency (`owner@demoagency.io` / `demo-password-123`),
creates an intake form, a template, a client, starts an onboarding
(which starts a real Temporal workflow), then **acts as the client**
through the real portal API — submits the intake form, uploads two
documents, connects both mock OAuth providers — and polls until the
workflow completes, printing the AI-generated kickoff brief and
dashboard summary at the end.

If it prints `✅ End-to-end demo flow completed successfully.`, the
whole stack — Postgres/RLS, FastAPI, Temporal, and the AI mock — is
wired up correctly.

---

## 7. Try it in the browser

1. Go to http://localhost:3000/login → log in with
   `owner@demoagency.io` / `demo-password-123` (or register a new agency).
2. **Dashboard** shows onboarding counts and time-to-start.
3. **Clients** → open the client `seed_demo.py` created → **Start
   onboarding** with the seeded template.
4. On the resulting instance page, click **Open client portal ↗** — this
   opens the real client-facing portal (no staff login needed, just the
   link) in a new tab. Submit the intake form, upload documents, connect
   both accounts.
5. Back on the staff instance page (auto-refreshes every 5s), watch the
   status move to `COMPLETED` and the AI kickoff brief appear.
6. Click **Query live workflow** — this queries the actual running
   Temporal workflow (not just the database), proving it's a live
   process.

---

## 8. Run the backend test suite

```bash
cd backend
.venv/bin/pytest -v
```

15 tests covering: health, auth (register/login/duplicate-email),
tenant isolation (Phase 1's critical test — org A cannot see org B's
data, verified through the real API), RBAC (Phase 2's full role matrix:
CLIENT/STAFF/ADMIN/OWNER), form version immutability (Phase 4's critical
test), and the AI mock extraction service.

These run against your real local Postgres (no separate test-database
fixture — see `CHANGELOG.md`), so Postgres must be running. Tests use
randomly-suffixed emails/org names so they're safe to re-run repeatedly
without manual cleanup.

---

## 9. Optional: real AI extraction via Groq

By default `GROQ_API_KEY` is unset, and document extraction uses a
deterministic mock (seeded by document content, so results are
reproducible) — the demo works fully without any API key, including
exercising both the auto-approve and human-review confidence paths.

To use real Groq extraction instead:
```bash
# in backend/.env
GROQ_API_KEY=gsk_your_key_here
```
No restart-proofing needed beyond restarting the API/worker processes to
pick up the new `.env` value.

---

## 10. Verifying Temporal survives a worker crash (Phase 7's critical test)

This is real, not simulated — Temporal's whole value proposition is that
workflow state survives worker restarts. To see it yourself:

1. Start an onboarding and submit the intake form via the portal (so the
   workflow is mid-flight, waiting on documents).
2. Kill the worker process hard: find its PID (`ps aux | grep app.worker`)
   and `kill -9 <pid>`.
3. Confirm it's unreachable: `GET /onboarding-instances/{id}/workflow-status`
   returns `"queryable": false`.
4. Restart the worker: `.venv/bin/python -m app.worker`.
5. Query again — `"queryable": true` and `form_submitted: true` is still
   there. Finish uploading documents/connecting accounts — it completes
   normally.

---

## 11. Seeing a reminder / BLOCKED status fire live

The workflow has a demo-shortened reminder timer (90 seconds, standing
in for the real 24h/48h/72h cadence in `docs/research.md`) — start an
onboarding and simply don't submit the intake form. After ~90 seconds:
- the instance's status flips to `BLOCKED` (visible on the dashboard)
- a reminder email is logged (`SELECT * FROM email_log ORDER BY sent_at DESC LIMIT 1;`)

Submitting the intake form afterward recovers it to `IN_PROGRESS` and it
proceeds normally. To make this instant for a live demo, lower
`reminder_delay_seconds` in `OnboardingWorkflowInput`
(`app/workflows/onboarding.py`) before starting the workflow.

---

## 12. Troubleshooting

**`invalid input syntax for type uuid: ""`** — RLS is enabled but the
request's tenant context wasn't set. Shouldn't happen through normal API
use; if you're querying the DB directly, run
`SET LOCAL app.current_org_id = '<org-uuid>';` first, or connect as
`onboarding_owner` (which bypasses RLS) for ad-hoc debugging.

**`alembic upgrade head` fails with "no schema has been selected to
create in"** — the `onboarding_owner` role is missing `USAGE` on the
`public` schema (this can happen if you drop/recreate the schema
manually). Fix: `./infrastructure/setup_db.sh` (safe to re-run, just
reapplies the grants from § 2).

**Temporal workflow won't start / `create_instance` hangs** — the worker
process isn't running, or the Temporal dev server isn't up. Check
`temporal operator cluster health --address 127.0.0.1:7233` returns
`SERVING`.

**Frontend can't reach the backend / CORS errors** — confirm
`CORS_ORIGINS` in `backend/.env` includes `http://localhost:3000` and
`NEXT_PUBLIC_API_URL` in `frontend/.env.local` points at
`http://127.0.0.1:8000`.

**Port already in use** — something from a previous run is still
running: `lsof -i :8000` / `:3000` / `:7233` / `:5432` / `:8080` and kill
the stale process.

---

## 13. Known limitations

See `CHANGELOG.md` for the full list of what's simplified vs. the
original architecture for demo purposes (mocked email/OAuth, local-disk
file storage instead of S3/MinIO, simplified RBAC, no test-database
isolation, etc.).
