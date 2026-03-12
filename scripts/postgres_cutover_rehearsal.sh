#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be set to the target Postgres database for rehearsal."
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
ARTIFACT_DIR="var/postgres-rehearsal/${STAMP}"
mkdir -p "${ARTIFACT_DIR}"

echo "[1/6] SQLite backup drill"
./scripts/sqlite_backup_restore_drill.sh

echo "[2/6] Baseline snapshot from current database (typically sqlite)"
python manage.py database_snapshot --output "${ARTIFACT_DIR}/baseline.json"

echo "[3/6] Run migrations against target Postgres"
DATABASE_URL="${DATABASE_URL}" python manage.py migrate --noinput

echo "[4/6] Candidate snapshot from target Postgres"
DATABASE_URL="${DATABASE_URL}" python manage.py database_snapshot --output "${ARTIFACT_DIR}/candidate.json"

echo "[5/6] Compare baseline vs candidate"
python manage.py compare_database_snapshots --left "${ARTIFACT_DIR}/baseline.json" --right "${ARTIFACT_DIR}/candidate.json"

echo "[6/6] Done"
echo "Artifacts: ${ARTIFACT_DIR}"

