#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/apps/skinmenu"
VENV="/home/deploy/venvs/skinmenu"
ENV_FILE="/etc/skinmenu/skinmenu.env"
SERVICE="skinmenu"
DJANGO_SETTINGS_MODULE="config.settings.production"
DEPLOY_STATE_FILE="$APP_DIR/.deploy_state"

log() { echo "[$(date -Is)] $*"; }
die() { log "ERROR: $*"; exit 1; }

cd "$APP_DIR"

[[ -f "$DEPLOY_STATE_FILE" ]] || die "no deploy state file at $DEPLOY_STATE_FILE"
TARGET="$(cat "$DEPLOY_STATE_FILE")"
[[ -n "$TARGET" ]] || die "deploy state file empty"

log "== Rolling back to: $TARGET =="

git fetch origin --prune
git checkout --detach "$TARGET"

# shellcheck disable=SC1090
source "$VENV/bin/activate"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

sudo -n systemctl restart "$SERVICE"
sudo -n systemctl --no-pager --full status "$SERVICE" | sed -n '1,80p'

python scripts/smoke_test.py

log "== Rollback complete =="
