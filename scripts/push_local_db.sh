#!/usr/bin/env bash
# Copy your local isat_recruiter database to Railway Postgres.
#
# Option A (recommended): copy DATABASE_PUBLIC_URL from Railway Variables.
#   export RAILWAY_DATABASE_URL='postgresql://...'
#   ./scripts/push_local_db.sh
#
# Option B: set individual Railway values (avoids URL/password encoding issues).
#   export RAILWAY_PG_HOST='....proxy.rlwy.net'
#   export RAILWAY_PG_PORT='38451'
#   export RAILWAY_PG_USER='postgres'
#   export RAILWAY_PG_PASSWORD='...'
#   export RAILWAY_PG_DATABASE='railway'
#   ./scripts/push_local_db.sh

set -euo pipefail

LOCAL_DB_NAME="${LOCAL_DB_NAME:-isat_recruiter}"
LOCAL_DB_USER="${LOCAL_DB_USER:-postgres}"
LOCAL_DB_HOST="${LOCAL_DB_HOST:-localhost}"
LOCAL_DB_PORT="${LOCAL_DB_PORT:-5432}"

build_psql_args() {
  # Prefer explicit PG_* vars when set (avoids stale RAILWAY_DATABASE_URL in shell).
  if [[ -n "${RAILWAY_PG_HOST:-}" ]]; then
    export PGHOST="$RAILWAY_PG_HOST"
    export PGPORT="${RAILWAY_PG_PORT:-5432}"
    export PGUSER="${RAILWAY_PG_USER:-postgres}"
    export PGPASSWORD="${RAILWAY_PG_PASSWORD:?Set RAILWAY_PG_PASSWORD}"
    export PGDATABASE="${RAILWAY_PG_DATABASE:-railway}"
    export PGSSLMODE="${PGSSLMODE:-require}"
    printf 'flags'
    return
  fi

  if [[ -n "${RAILWAY_DATABASE_URL:-}" ]]; then
    local url="$RAILWAY_DATABASE_URL"
    if [[ "$url" == *'${{'* ]]; then
      echo "RAILWAY_DATABASE_URL still contains Railway placeholders like \${{PGPASSWORD}}."
      echo "Copy the resolved value from Railway Variables (copy icon), or use Option B env vars."
      exit 1
    fi
    if [[ "$url" != *"sslmode="* ]]; then
      if [[ "$url" == *"?"* ]]; then
        url="${url}&sslmode=require"
      else
        url="${url}?sslmode=require"
      fi
    fi
    printf '%s' "$url"
    return
  fi

  echo "Set RAILWAY_DATABASE_URL or the RAILWAY_PG_* variables."
  exit 1
}

PSQL_TARGET="$(build_psql_args)"

echo "Testing Railway connection..."
if [[ "$PSQL_TARGET" == "flags" ]]; then
  psql -c "SELECT 1;" >/dev/null
else
  psql "$PSQL_TARGET" -c "SELECT 1;" >/dev/null
fi
echo "Connected."

echo "Dumping local database '${LOCAL_DB_NAME}' (clean replace on Railway)..."
if [[ "$PSQL_TARGET" == "flags" ]]; then
  pg_dump \
    --host="$LOCAL_DB_HOST" \
    --port="$LOCAL_DB_PORT" \
    --username="$LOCAL_DB_USER" \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    "$LOCAL_DB_NAME" \
  | psql
else
  pg_dump \
    --host="$LOCAL_DB_HOST" \
    --port="$LOCAL_DB_PORT" \
    --username="$LOCAL_DB_USER" \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    "$LOCAL_DB_NAME" \
  | psql "$PSQL_TARGET"
fi

echo "Done."
