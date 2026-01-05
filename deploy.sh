#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/apps/skinmenu"
VENV="/home/deploy/venvs/skinmenu"
ENV_FILE="/etc/skinmenu/skinmenu.env"
SERVICE="skinmenu"
DJANGO_SETTINGS_MODULE="config.settings.production"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: working tree is dirty. Commit/stash before deploying."
  git status -sb
  exit 1
fi


cd "$APP_DIR"

echo "== Deploying $(date -Is) =="
echo "== Git status before =="
git status -sb || true

echo "== Fetch & fast-forward main =="
git fetch origin --prune
git checkout main
git pull --ff-only origin main

echo "== Python env =="
source "$VENV/bin/activate"
set -a
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

echo "== Install Python deps =="
pip install -r requirements.txt

# If you have node build steps, add them here (npm ci && npm run build)

echo "== Django checks =="
python manage.py check --deploy || true

echo "== Migrate =="
python manage.py migrate --noinput

echo "== Collectstatic =="
# Make sure manifest is rebuilt
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
