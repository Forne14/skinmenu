#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/deploy/apps/skinmenu"
DEPLOY_SCRIPT="$APP_DIR/deploy.sh"
BRANCH="main"
REMOTE="origin"

log() {
  echo "[$(date -Is)] $*"
}

die() {
  log "ERROR: $*"
  exit 1
}

cd "$APP_DIR" || die "cannot cd to $APP_DIR"

log "== Sync repo to $REMOTE/$BRANCH =="

# Ensure this is a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git repo"

# Fetch latest refs
git fetch "$REMOTE" --prune

# Ensure branch exists remotely
git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH" \
  || die "remote branch $REMOTE/$BRANCH not found"

# Switch to branch (even if detached)
git checkout "$BRANCH"

# HARD reset to remote branch
git reset --hard "$REMOTE/$BRANCH"

# Remove untracked files/dirs (including old staticfiles, junk, etc)
git clean -fd

log "== Repo now at =="
git --no-pager log -1 --oneline

# Sanity: deploy.sh must exist and be executable
[[ -x "$DEPLOY_SCRIPT" ]] || die "deploy.sh missing or not executable"

log "== Handing off to deploy.sh =="
exec "$DEPLOY_SCRIPT"
