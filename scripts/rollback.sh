#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/apps/skinmenu"
VENV="/home/deploy/venvs/skinmenu"
ENV_FILE="/etc/skinmenu/skinmenu.env"
SERVICE="skinmenu"
DJANGO_SETTINGS_MODULE="config.settings.production"

DEPLOY_STATE_FILE="$APP_DIR/.deploy_state"
DEPLOY_LOG_FILE="$APP_DIR/.deploy_log"
LOCK_FILE="/tmp/skinmenu-deploy.lock"

log() { echo "[$(date -Is)] $*"; }

cd "$APP_DIR"

exec 200>"$LOCK_FILE"
flock -n 200 || { log "ERROR: another deploy is in progress"; exit 1; }

if [[ ! -f "$DEPLOY_STATE_FILE" ]]; then
  log "ERROR: no deploy state found at $DEPLOY_STATE_FILE"
  exit 1
fi

CURRENT_SHA="$(git rev-parse HEAD)"
LAST_DEPLOYED_SHA="$(cat "$DEPLOY_STATE_FILE")"

log "== Rollback requested =="
log "Current HEAD: $CURRENT_SHA"
log "Last deployed recorded: $LAST_DEPLOYED_SHA"

# If user passed a SHA, rollback to that. Otherwise rollback to previous entry in log.
TARGET_SHA="${1:-}"

if [[ -z "$TARGET_SHA" ]]; then
  # Find previous deployed SHA from log
  if [[ ! -f "$DEPLOY_LOG_FILE" ]]; then
    log "ERROR: no deploy log found at $DEPLOY_LOG_FILE (pass a SHA to rollback)"
    exit 1
  fi

  # Grab the second-to-last deployed sha
  TARGET_SHA="$(tac "$DEPLOY_LOG_FILE" | grep -Eo 'deployed=[0-9a-f]{7,40}' | sed 's/deployed=//' | sed -n '2p' || true)"

  if [[ -z "$TARGET_SHA" ]]; then
    log "ERROR: could not infer previous deploy SHA (pass a SHA explicitly)"
    exit 1
  fi
fi

log "Rolling back to: $TARGET_SHA"

git fetch origin --prune
git checkout --detach "$TARGET_SHA"

# shellcheck disable=SC1090
source "$VENV/bin/activate"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

log "== Migrate =="
python manage.py migrate --noinput

log "== Collectstatic =="
python manage.py collectstatic --noinput --clear

log "== Restart service =="
sudo systemctl restart "$SERVICE"
sudo systemctl --no-pager --full status "$SERVICE" | sed -n '1,60p'

log "== Smoke test =="
python scripts/smoke_test.py

echo "$TARGET_SHA" > "$DEPLOY_STATE_FILE"
echo "[$(date -Is)] rollback_to=$TARGET_SHA from=$CURRENT_SHA" >> "$DEPLOY_LOG_FILE"

log "== Rollback done =="
