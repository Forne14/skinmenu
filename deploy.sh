#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/apps/skinmenu"
VENV="/home/deploy/venvs/skinmenu"
ENV_FILE="/etc/skinmenu/skinmenu.env"
SERVICE="skinmenu"
DJANGO_SETTINGS_MODULE="config.settings.production"

LOCK_FILE="/tmp/skinmenu-deploy.lock"
DEPLOY_STATE_FILE="$APP_DIR/.deploy_state"
DEPLOY_LOG_FILE="$APP_DIR/.deploy_log"

# Optional: DEPLOY_REF=main (default), or DEPLOY_REF=<branch>, or DEPLOY_REF=<tag>, or DEPLOY_REF=<sha>
DEPLOY_REF="${DEPLOY_REF:-main}"

log() { echo "[$(date -Is)] $*"; }
die() { log "ERROR: $*"; exit 1; }

cd "$APP_DIR"

# Prevent concurrent deploys
exec 200>"$LOCK_FILE"
flock -n 200 || die "another deploy is in progress"

log "== Deploying (ref=$DEPLOY_REF) =="

# Sanity: git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "$APP_DIR is not a git repo"

# Refuse dirty tree
if ! git diff --quiet || ! git diff --cached --quiet; then
  log "Working tree is dirty:"
  git status -sb || true
  die "commit/stash/reset before deploying"
fi

# Ensure origin exists
git remote get-url origin >/dev/null 2>&1 || die "git remote 'origin' not configured"

PRE_SHA="$(git rev-parse HEAD)"
log "== Current HEAD before fetch: $PRE_SHA =="

log "== Fetch origin =="
git fetch origin --prune

# Resolve target commit
TARGET_COMMIT=""
if [[ "$DEPLOY_REF" == "origin/"* ]]; then
  TARGET_COMMIT="$(git rev-parse "$DEPLOY_REF" 2>/dev/null || true)"
else
  if git show-ref --verify --quiet "refs/remotes/origin/$DEPLOY_REF"; then
    TARGET_COMMIT="$(git rev-parse "origin/$DEPLOY_REF")"
  else
    TARGET_COMMIT="$(git rev-parse "$DEPLOY_REF" 2>/dev/null || true)"
  fi
fi
[[ -n "$TARGET_COMMIT" ]] || die "could not resolve DEPLOY_REF=$DEPLOY_REF"

log "== Target commit: $TARGET_COMMIT =="

log "== Checkout target commit (detached HEAD) =="
git checkout --detach "$TARGET_COMMIT"

CUR_SHA="$(git rev-parse HEAD)"
log "== Deploying commit: $CUR_SHA =="

# Python env
[[ -d "$VENV" ]] || die "venv not found: $VENV"
# shellcheck disable=SC1090
source "$VENV/bin/activate"

# Load env file
[[ -f "$ENV_FILE" ]] || die "env file not found: $ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

# Required env guards
: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY missing (from $ENV_FILE)}"
: "${DJANGO_ALLOWED_HOSTS:?DJANGO_ALLOWED_HOSTS missing (from $ENV_FILE)}"

log "== Install Python deps =="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "== Django checks (deploy) =="
python manage.py check --deploy

log "== Migration sanity (fail if missing migrations) =="
python manage.py makemigrations --check --dry-run

log "== Migrate =="
python manage.py migrate --noinput

log "== Collectstatic (clear + rebuild) =="
python manage.py collectstatic --noinput --clear

log "== Verify static manifest contains required picker files (best-effort) =="
python - <<'PY'
import json
from pathlib import Path

p = Path("staticfiles/staticfiles.json")
if not p.exists():
    print("No staticfiles.json at", p, "(ok if not using Manifest storage)")
    raise SystemExit(0)

data = json.loads(p.read_text())
paths = data.get("paths", {})
need = [
    "css/media-position-picker.css",
    "js/media-position-picker.js",
]
missing = [n for n in need if n not in paths]
print("manifest missing:", missing) if missing else print("manifest ok")
assert not missing
PY

log "== Restart service =="
sudo -n systemctl restart "$SERVICE" || die "failed to restart $SERVICE"
sudo -n systemctl --no-pager --full status "$SERVICE" | sed -n '1,80p'

log "== Smoke test (Django + nginx) =="
python scripts/smoke_test.py

# Record deployment state
PREV_SHA=""
if [[ -f "$DEPLOY_STATE_FILE" ]]; then
  PREV_SHA="$(cat "$DEPLOY_STATE_FILE" || true)"
fi
echo "$CUR_SHA" > "$DEPLOY_STATE_FILE"
echo "[$(date -Is)] deployed=$CUR_SHA previous=${PREV_SHA:-none} pre=$PRE_SHA ref=$DEPLOY_REF" >> "$DEPLOY_LOG_FILE"

log "== Done =="
