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

# Optional:
#   DEPLOY_REF=main            (default)
#   DEPLOY_REF=origin/main     (allowed)
#   DEPLOY_REF=<branch-name>   (allowed if exists on origin)
DEPLOY_REF="${DEPLOY_REF:-main}"

log() { echo "[$(date -Is)] $*"; }
die() { log "ERROR: $*"; exit 1; }

cd "$APP_DIR"

# ---- Single-deploy lock (prevents concurrent deploys)
exec 200>"$LOCK_FILE"
flock -n 200 || die "another deploy is in progress"

log "== Deploying (ref=$DEPLOY_REF) =="

# ---- Sanity: ensure this is a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "$APP_DIR is not a git repo"

# ---- Refuse to deploy with local modifications
if ! git diff --quiet || ! git diff --cached --quiet; then
  log "Working tree is dirty:"
  git status -sb || true
  die "commit/stash/reset before deploying"
fi

# ---- Ensure origin exists
git remote get-url origin >/dev/null 2>&1 || die "git remote 'origin' not configured"

# ---- Record PRE-PULL SHA for rollback safety
PRE_PULL_SHA="$(git rev-parse HEAD)"
log "== Current HEAD before pull: $PRE_PULL_SHA =="

log "== Fetch origin =="
git fetch origin --prune

# ---- Resolve target ref to a commit
# Allow:
#   - "main"  -> origin/main
#   - "origin/main"
#   - any branch that exists on origin (e.g. "feature/x")
TARGET_COMMIT=""
if [[ "$DEPLOY_REF" == "origin/"* ]]; then
  TARGET_COMMIT="$(git rev-parse "$DEPLOY_REF" 2>/dev/null || true)"
else
  # prefer origin/<branch>
  if git show-ref --verify --quiet "refs/remotes/origin/$DEPLOY_REF"; then
    TARGET_COMMIT="$(git rev-parse "origin/$DEPLOY_REF")"
  else
    # or direct ref if valid (tags/sha)
    TARGET_COMMIT="$(git rev-parse "$DEPLOY_REF" 2>/dev/null || true)"
  fi
fi

[[ -n "$TARGET_COMMIT" ]] || die "could not resolve DEPLOY_REF=$DEPLOY_REF"

log "== Target commit: $TARGET_COMMIT =="

# ---- Force local main branch to match the target (fast-forward only when DEPLOY_REF=main)
# Safer approach: deploy detached HEAD at target commit (no 'server ahead of local' surprises)
log "== Checkout target commit (detached HEAD) =="
git checkout --detach "$TARGET_COMMIT"

CURRENT_SHA="$(git rev-parse HEAD)"
log "== Deploying commit: $CURRENT_SHA =="

# ---- Python env
[[ -d "$VENV" ]] || die "venv not found: $VENV"
# shellcheck disable=SC1090
source "$VENV/bin/activate"

# ---- Load env file
[[ -f "$ENV_FILE" ]] || die "env file not found: $ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"

# ---- Minimal required env guards
: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY missing (from $ENV_FILE)}"
: "${DJANGO_ALLOWED_HOSTS:?DJANGO_ALLOWED_HOSTS missing (from $ENV_FILE)}"

log "== Install Python deps =="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "== Django checks (deploy) =="
python manage.py check --deploy

log "== Migration sanity (FAIL if missing migrations) =="
python manage.py makemigrations --check --dry-run

log "== Migrate =="
python manage.py migrate --noinput

log "== Collectstatic (clear + rebuild manifest) =="
python manage.py collectstatic --noinput --clear

log "== Restart service =="
sudo -n systemctl restart "$SERVICE" || die "failed to restart $SERVICE"
sudo -n systemctl --no-pager --full status "$SERVICE" | sed -n '1,80p'

log "== Smoke test admin login =="
python scripts/smoke_test.py

# ---- Record deployment
PREV_SHA=""
if [[ -f "$DEPLOY_STATE_FILE" ]]; then
  PREV_SHA="$(cat "$DEPLOY_STATE_FILE" || true)"
fi
echo "$CURRENT_SHA" > "$DEPLOY_STATE_FILE"
echo "[$(date -Is)] deployed=$CURRENT_SHA previous=${PREV_SHA:-none} pre_pull=$PRE_PULL_SHA ref=$DEPLOY_REF" >> "$DEPLOY_LOG_FILE"

log "== Done =="
