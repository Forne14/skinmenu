#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/apps/skinmenu"
VENV="/home/deploy/venvs/skinmenu"
ENV_FILE="/etc/skinmenu/skinmenu.env"
SERVICE="skinmenu"
DJANGO_SETTINGS_MODULE="config.settings.production"

cd "$APP_DIR"

# Sanity: ensure this is a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: $APP_DIR is not a git repo"
  exit 1
fi

# Refuse to deploy with local modifications
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: working tree is dirty. Commit/stash before deploying."
  git status -sb
  exit 1
fi

echo "== Deploying $(date -Is) =="
echo "== Git status before =="
git status -sb || true

echo "== Fetch & fast-forward main =="
git fetch origin --prune
git checkout main
git pull --ff-only origin main

echo "== Python env =="
source "$VENV/bin/activate"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

echo "== Install Python deps =="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# If you have node build steps, add them here (npm ci && npm run build)

echo "== Django checks (deploy) =="
python manage.py check --deploy

echo "== Migrate =="
python manage.py makemigrations --noinput
python manage.py migrate --noinput


echo "== Collectstatic =="
rm -f "$APP_DIR/static/staticfiles.json" || true
python manage.py collectstatic --noinput

echo "== Restart service =="
sudo systemctl restart "$SERVICE"
sudo systemctl --no-pager --full status "$SERVICE" | sed -n '1,40p'

echo "== Smoke test admin login =="
python - <<'PY'
import os, django
from django.test import Client
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()
c = Client(HTTP_HOST="skin-menu.co.uk", wsgi_url_scheme="https")
r = c.get("/admin/login/")
print("status:", r.status_code)
assert r.status_code == 200, r.status_code
PY

echo "== Done =="
