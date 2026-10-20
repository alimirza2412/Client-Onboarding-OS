# Infrastructure

## `setup_db.sh`

One-command PostgreSQL setup for local development:

```bash
./infrastructure/setup_db.sh
```

Installs PostgreSQL if it's missing, starts it, creates the `onboarding_os`
database, and creates the two roles decision D2 requires
(`docs/decisions.md`) — `onboarding_owner` for migrations and
`onboarding_app` (non-owner) for the running app, so Row-Level Security
actually applies to it.

Safe to re-run any time — every step checks whether it's already done
before doing it, so re-running won't error or touch existing data/tables.

Override defaults via environment variables if you want different
credentials (must then match `backend/.env`):

```bash
DB_NAME=my_db OWNER_PASSWORD=x APP_PASSWORD=y ./infrastructure/setup_db.sh
```

See `DEMO_SETUP.md` for the full setup flow (this script replaces its
manual SQL steps — the manual version is still documented there too, for
reference/troubleshooting).

## Temporal

No setup script needed — it's a single downloaded binary with no
database/roles to configure. See `DEMO_SETUP.md` § 3.

## Not used in this demo

Redis and MinIO/S3 are named in the architecture for later phases but
aren't part of this demo's scope — see `CHANGELOG.md` for why.
