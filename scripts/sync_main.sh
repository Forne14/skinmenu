#!/usr/bin/env bash
set -euo pipefail

git status -sb
git stash push -u -m "pre-sync $(date -Is)" || true

git fetch origin --prune
git checkout main
git reset --hard origin/main

echo "Local main now matches origin/main."
git status -sb
