#!/usr/bin/env bash
set -euo pipefail

# Local-only control sequence to gate a production migration decision.
# This does not deploy; it validates preconditions and rehearses sqlite->postgres parity.

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  echo "DJANGO_SECRET_KEY must be set."
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be set to target Postgres."
  exit 1
fi

echo "[control 1/3] pre-cutover gate"
PYTHON_BIN="${PYTHON_BIN}" ./scripts/pre_cutover_check.sh

echo "[control 2/3] full sqlite->postgres rehearsal"
REHEARSAL_OUTPUT="$(PYTHON_BIN="${PYTHON_BIN}" ./scripts/postgres_cutover_rehearsal.sh)"
echo "${REHEARSAL_OUTPUT}"

ARTIFACT_DIR="$(printf "%s\n" "${REHEARSAL_OUTPUT}" | sed -n 's/^Artifacts: //p' | tail -n 1)"
if [[ -z "${ARTIFACT_DIR}" ]]; then
  echo "Failed to parse artifact directory from rehearsal output."
  exit 1
fi

BASELINE="${ARTIFACT_DIR}/baseline.json"
CANDIDATE="${ARTIFACT_DIR}/candidate.json"

if [[ ! -f "${BASELINE}" || ! -f "${CANDIDATE}" ]]; then
  echo "Missing rehearsal snapshots in ${ARTIFACT_DIR}"
  exit 1
fi

echo "[control 3/3] explicit parity re-check"
"${PYTHON_BIN}" manage.py compare_database_snapshots --left "${BASELINE}" --right "${CANDIDATE}"

echo "local_cutover_control_sequence: ok"
echo "gate_artifacts=${ARTIFACT_DIR}"
