#!/usr/bin/env bash
#
# One-command Postgres setup for the Client Onboarding OS demo.
#
# Does exactly what DEMO_SETUP.md § 2 walks through by hand: installs
# PostgreSQL if needed, starts it, creates the onboarding_os database,
# and creates the two roles decision D2 (docs/decisions.md) requires —
# onboarding_owner (migrations) and onboarding_app (the running app,
# non-owner so Row-Level Security actually applies to it).
#
# Safe to re-run: every step checks "does this already exist" first, so
# running this twice (or after a partial failure) won't error out or
# duplicate anything.
#
# Usage:
#   ./setup_db.sh
#
# Override defaults via environment variables if needed, e.g.:
#   DB_NAME=my_db OWNER_PASSWORD=x APP_PASSWORD=y ./setup_db.sh
# (Must match backend/.env's DATABASE_URL / ALEMBIC_DATABASE_URL if you do.)

set -euo pipefail

DB_NAME="${DB_NAME:-onboarding_os}"
OWNER_USER="${OWNER_USER:-onboarding_owner}"
OWNER_PASSWORD="${OWNER_PASSWORD:-onboarding_owner_pw}"
APP_USER="${APP_USER:-onboarding_app}"
APP_PASSWORD="${APP_PASSWORD:-onboarding_app_pw}"
PG_VERSION="${PG_VERSION:-16}"

# Use sudo unless we're already root (e.g. inside some containers)
SUDO=""
if [ "$(id -u)" != "0" ]; then
  SUDO="sudo"
fi

run_sql() {
  # Runs a SQL string as the postgres superuser, against $1 (database name)
  local db="$1"
  local sql="$2"
  $SUDO su postgres -c "psql -v ON_ERROR_STOP=1 -d '${db}' -c \"${sql}\""
}

echo "==> Checking for PostgreSQL..."
if ! command -v psql >/dev/null 2>&1; then
  echo "==> PostgreSQL not found — installing..."
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq postgresql postgresql-contrib
else
  echo "    Found: $(psql --version)"
fi

echo "==> Starting PostgreSQL..."
if command -v pg_ctlcluster >/dev/null 2>&1; then
  $SUDO pg_ctlcluster "${PG_VERSION}" main start 2>/dev/null || true
else
  $SUDO service postgresql start 2>/dev/null || $SUDO systemctl start postgresql 2>/dev/null || true
fi
sleep 2

echo "==> Waiting for PostgreSQL to accept connections..."
for i in $(seq 1 15); do
  if $SUDO su postgres -c "pg_isready" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Creating database '${DB_NAME}' (if it doesn't already exist)..."
DB_EXISTS=$($SUDO su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\"")
if [ "$DB_EXISTS" != "1" ]; then
  $SUDO su postgres -c "psql -c 'CREATE DATABASE ${DB_NAME};'"
  echo "    Created."
else
  echo "    Already exists — skipping."
fi

echo "==> Creating role '${OWNER_USER}' (migrations, table owner) (if needed)..."
$SUDO su postgres -c "psql" <<EOF
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${OWNER_USER}') THEN
      CREATE ROLE ${OWNER_USER} WITH LOGIN PASSWORD '${OWNER_PASSWORD}' CREATEDB;
   END IF;
END
\$\$;
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${OWNER_USER};
EOF

echo "==> Creating role '${APP_USER}' (runtime app — non-owner, so RLS applies) (if needed)..."
$SUDO su postgres -c "psql" <<EOF
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_USER}') THEN
      CREATE ROLE ${APP_USER} WITH LOGIN PASSWORD '${APP_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
   END IF;
END
\$\$;
GRANT CONNECT ON DATABASE ${DB_NAME} TO ${APP_USER};
EOF

echo "==> Setting schema privileges (idempotent — GRANT is safe to repeat)..."
run_sql "${DB_NAME}" "GRANT USAGE ON SCHEMA public TO ${APP_USER};"
run_sql "${DB_NAME}" "GRANT USAGE, CREATE ON SCHEMA public TO ${OWNER_USER};"
run_sql "${DB_NAME}" "ALTER DEFAULT PRIVILEGES FOR ROLE ${OWNER_USER} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_USER};"

echo "==> Verifying app role can actually connect over TCP..."
if PGPASSWORD="${APP_PASSWORD}" psql -h 127.0.0.1 -p 5432 -U "${APP_USER}" -d "${DB_NAME}" -c "SELECT 1;" >/dev/null 2>&1; then
  echo
  echo "✅ PostgreSQL is set up and ready."
  echo
  echo "Next step:"
  echo "  cd backend && .venv/bin/alembic upgrade head"
else
  echo
  echo "⚠️  Setup ran, but a test connection as '${APP_USER}' failed."
  echo "    This is usually a pg_hba.conf auth issue. Check that a line like:"
  echo "      host    all    all    127.0.0.1/32    scram-sha-256"
  echo "    exists in /etc/postgresql/${PG_VERSION}/main/pg_hba.conf, then:"
  echo "      ${SUDO} pg_ctlcluster ${PG_VERSION} main restart"
  exit 1
fi
