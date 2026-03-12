#!/usr/bin/env bash
set -euo pipefail

VENV="${VENV:-.venv}"
if [[ -d "${VENV}" ]]; then
  # shellcheck disable=SC1090
  source "${VENV}/bin/activate"
fi

python manage.py check
python manage.py validate_integrations_config
python manage.py makemigrations --check --dry-run
python manage.py test --settings=config.settings.test
python manage.py audit_content_integrity
python manage.py audit_legacy_content
python scripts/postgres_readiness.py

echo "pre_release_check: ok"

