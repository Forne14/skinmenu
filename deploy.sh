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

DEPLOY_REF="${DEPLOY_REF:-main}"

log() { echo "[$(date -Is)] $*"; }
die() { log "ERROR: $*"; exit 1; }

cd "$APP_DIR"

exec 200>"$LOCK_FILE"
flock -n 200 || die "another deploy is in progress"

log "== Deploying (ref=$DEPLOY_REF) =="

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "$APP_DIR is not a git repo"

if ! git diff --quiet || ! git diff --cached --quiet; then
  log "Working tree is dirty:"
  git status -sb || true
  die "commit/stash/reset before deploying"
fi

git remote get-url origin >/dev/null 2>&1 || die "git remote 'origin' not configured"

CURRENT_HEAD="$(git rev-parse HEAD)"
log "== Current HEAD before fetch: $CURRENT_HEAD =="

log "== Fetch origin =="
git fetch origin --prune

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

DEPLOY_SHA="$(git rev-parse HEAD)"
log "== Deploying commit: $DEPLOY_SHA =="

[[ -d "$VENV" ]] || die "venv not found: $VENV"
# shellcheck disable=SC1090
source "$VENV/bin/activate"

[[ -f "$ENV_FILE" ]] || die "env file not found: $ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

# Make imports reliable no matter where python is launched from
export PYTHONPATH="$APP_DIR"

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
test -f "$APP_DIR/staticfiles/staticfiles.json" && echo "manifest ok"

log "== Restart service =="
sudo -n systemctl restart "$SERVICE" || die "failed to restart $SERVICE"
sudo -n systemctl --no-pager --full status "$SERVICE" | sed -n '1,80p'

log "== Restart rqworker service =="
sudo -n systemctl restart "skinmenu-rqworker" || die "failed to restart skinmenu-rqworker"
sudo -n systemctl --no-pager --full status "skinmenu-rqworker" | sed -n '1,80p'

log "== Smoke test (Django + nginx) =="
python scripts/smoke_test.py

PREV_SHA=""
if [[ -f "$DEPLOY_STATE_FILE" ]]; then
  PREV_SHA="$(cat "$DEPLOY_STATE_FILE" || true)"
fi
echo "$DEPLOY_SHA" > "$DEPLOY_STATE_FILE"
echo "[$(date -Is)] deployed=$DEPLOY_SHA previous=${PREV_SHA:-none} ref=$DEPLOY_REF" >> "$DEPLOY_LOG_FILE"

log "== Done =="
