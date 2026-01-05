#!/usr/bin/env bash
set -euo pipefail

# Adjust if your venv/env differs locally
VENV="${VENV:-.venv}"
ENV_FILE="${ENV_FILE:-.env}"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

if [[ -d "$VENV" ]]; then
  source "$VENV/bin/activate"
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

export DJANGO_SETTINGS_MODULE

python manage.py check
python manage.py migrate --plan
python manage.py collectstatic --noinput
