#!/usr/bin/env bash
set -euo pipefail

VENV="${VENV:-.venv}"
if [[ -d "${VENV}" ]]; then
  # shellcheck disable=SC1090
  source "${VENV}/bin/activate"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -x "${VENV}/bin/python" ]]; then
  PYTHON_BIN="${VENV}/bin/python"
fi

"${PYTHON_BIN}" manage.py check
"${PYTHON_BIN}" manage.py validate_integrations_config
"${PYTHON_BIN}" manage.py makemigrations --check --dry-run
"${PYTHON_BIN}" manage.py test --settings=config.settings.test
"${PYTHON_BIN}" manage.py audit_content_integrity
"${PYTHON_BIN}" manage.py audit_legacy_content
"${PYTHON_BIN}" scripts/postgres_readiness.py

echo "pre_release_check: ok"
