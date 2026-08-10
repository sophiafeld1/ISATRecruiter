#!/usr/bin/env bash
# Copy your local isat_recruiter database to Railway Postgres.
#
# Usage:
#   export RAILWAY_DATABASE_URL="postgresql://user:pass@host:port/railway"
#   ./scripts/push_local_db.sh
#
# Get RAILWAY_DATABASE_URL from Railway → Postgres service → Connect → Public URL

set -euo pipefail

if [[ -z "${RAILWAY_DATABASE_URL:-}" ]]; then
  echo "Set RAILWAY_DATABASE_URL to your Railway Postgres connection string."
  exit 1
fi

LOCAL_DB_NAME="${LOCAL_DB_NAME:-isat_recruiter}"
LOCAL_DB_USER="${LOCAL_DB_USER:-postgres}"
LOCAL_DB_HOST="${LOCAL_DB_HOST:-localhost}"
LOCAL_DB_PORT="${LOCAL_DB_PORT:-5432}"

echo "Dumping local database '${LOCAL_DB_NAME}'..."
pg_dump \
  --host="$LOCAL_DB_HOST" \
  --port="$LOCAL_DB_PORT" \
  --username="$LOCAL_DB_USER" \
  --format=plain \
  --no-owner \
  --no-acl \
  "$LOCAL_DB_NAME" \
| psql "$RAILWAY_DATABASE_URL"

echo "Done. Enable pgvector if needed:"
echo '  psql "$RAILWAY_DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"'
