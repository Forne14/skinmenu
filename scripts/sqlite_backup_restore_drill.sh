#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-db.sqlite3}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="var/sqlite-drills"
BACKUP_PATH="${BACKUP_DIR}/db-${STAMP}.sqlite3"
RESTORE_PATH="${BACKUP_DIR}/restore-${STAMP}.sqlite3"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_PATH}" ]]; then
  echo "Missing sqlite database at ${DB_PATH}"
  exit 1
fi

cp "${DB_PATH}" "${BACKUP_PATH}"
cp "${BACKUP_PATH}" "${RESTORE_PATH}"

echo "Backup created: ${BACKUP_PATH}"
echo "Restore copy:  ${RESTORE_PATH}"

sqlite3 "${RESTORE_PATH}" "PRAGMA integrity_check;" | grep -q "^ok$"
echo "Integrity check: ok"

echo "Drill complete."

