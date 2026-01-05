#!/usr/bin/env bash
set -euo pipefail

git status -sb
echo "This will discard uncommitted changes and reset to origin/main."
read -r -p "Type YES to continue: " ans
[[ "$ans" == "YES" ]]

git fetch origin --prune
git checkout main
git reset --hard origin/main
git clean -fd

echo "Server repo now clean and matches origin/main."
git status -sb
