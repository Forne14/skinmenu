#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be set to the target Postgres database for rehearsal."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
ARTIFACT_DIR="var/postgres-rehearsal/${STAMP}"
mkdir -p "${ARTIFACT_DIR}"

echo "[1/6] SQLite backup drill"
./scripts/sqlite_backup_restore_drill.sh

echo "[2/6] Baseline snapshot from current database (typically sqlite)"
env -u DATABASE_URL "${PYTHON_BIN}" manage.py database_snapshot --output "${ARTIFACT_DIR}/baseline.json"

echo "[3/6] Export source data fixture"
env -u DATABASE_URL "${PYTHON_BIN}" manage.py dumpdata \
  --exclude contenttypes \
  --exclude django_rq \
  --exclude wagtailsearch \
  --exclude wagtailcore.referenceindex \
  --exclude wagtailcore.modellogentry \
  --exclude wagtailcore.pagelogentry \
  --exclude auth.permission \
  --output "${ARTIFACT_DIR}/source.json"

echo "[4/8] Run migrations against target Postgres"
DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" manage.py migrate --noinput

echo "[5/8] Reset target Postgres data"
DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" manage.py flush --noinput

echo "[5.5/8] Restore locale seed required by Wagtail before fixture load"
DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" manage.py shell -c "from wagtail.models import Locale; from django.conf import settings; codes={settings.LANGUAGE_CODE.lower(), settings.LANGUAGE_CODE.lower().replace('_','-').split('-')[0], 'en'}; [Locale.objects.get_or_create(language_code=code) for code in sorted(codes) if code]"

echo "[6/8] Load source fixture into target Postgres"
DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" manage.py loaddata "${ARTIFACT_DIR}/source.json"

echo "[7/8] Candidate snapshot from target Postgres"
DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" manage.py database_snapshot --output "${ARTIFACT_DIR}/candidate.json"

echo "[8/8] Compare baseline vs candidate"
"${PYTHON_BIN}" manage.py compare_database_snapshots --left "${ARTIFACT_DIR}/baseline.json" --right "${ARTIFACT_DIR}/candidate.json"

echo "Done"
echo "Artifacts: ${ARTIFACT_DIR}"
