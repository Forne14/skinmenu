#!/usr/bin/env bash
set -euo pipefail

BRANCH="${1:-hotfix/$(date +%Y%m%d-%H%M%S)}"

git status -sb
git checkout -b "$BRANCH"
git add -A
git commit -m "Hotfix on server: $BRANCH"
git push -u origin "$BRANCH"

echo
echo "Pushed $BRANCH. Open a PR: $BRANCH -> main"
