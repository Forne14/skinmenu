#!/usr/bin/env bash
set -euo pipefail

VENV="${VENV:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x "${VENV}/bin/python" ]]; then
  PYTHON_BIN="${VENV}/bin/python"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python interpreter not executable: ${PYTHON_BIN}"
  exit 1
fi

if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  echo "DJANGO_SECRET_KEY must be set."
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be set to target Postgres."
  exit 1
fi

if [[ "${DATABASE_URL}" != postgres://* && "${DATABASE_URL}" != postgresql://* ]]; then
  echo "DATABASE_URL must use postgres:// or postgresql://"
  exit 1
fi

if [[ ! -f "db.sqlite3" ]]; then
  echo "Source sqlite database missing at db.sqlite3"
  exit 1
fi

mkdir -p var/postgres-rehearsal
if [[ ! -w "var/postgres-rehearsal" ]]; then
  echo "Artifact directory is not writable: var/postgres-rehearsal"
  exit 1
fi

echo "[1/7] Verify Python dependencies"
"${PYTHON_BIN}" -c "import django, psycopg2"

echo "[2/7] Verify target Postgres connectivity"
DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute('SELECT 1'); print(c.fetchone()[0])" >/dev/null

echo "[3/7] Run Django system checks"
"${PYTHON_BIN}" manage.py check

echo "[4/7] Validate integrations configuration"
"${PYTHON_BIN}" manage.py validate_integrations_config

echo "[5/7] Ensure no missing migrations"
"${PYTHON_BIN}" manage.py makemigrations --check --dry-run

echo "[6/7] Verify sqlite backup/restore drill"
./scripts/sqlite_backup_restore_drill.sh

echo "[7/7] Verify snapshot tooling"
env -u DATABASE_URL "${PYTHON_BIN}" manage.py database_snapshot --output /tmp/skinmenu_baseline_check.json >/dev/null
rm -f /tmp/skinmenu_baseline_check.json

echo "pre_cutover_check: ok"
