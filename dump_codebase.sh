#!/usr/bin/env bash
set -euo pipefail

# Dump a Django/Wagtail codebase into a single text file.
# Run from repo root.
#
# Usage:
#   ./dump_codebase.sh
#   ./dump_codebase.sh -o codebase-skinmenu.txt

OUTFILE="codebase-skinmenu.txt"

while getopts ":o:" opt; do
  case "$opt" in
    o) OUTFILE="$OPTARG" ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 2
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 2
      ;;
  esac
done

: > "$OUTFILE"

echo "Writing dump to: $OUTFILE" >&2

# -----------------------------
# Directories to prune entirely
# -----------------------------
PRUNE_DIRS=(
  ".git"
  ".venv" "venv"
  "__pycache__"
  "node_modules"
  "media"
  "static"          # collected output in your repo → huge
  "staticfiles"
  ".cache"
  ".pytest_cache"
  ".ruff_cache"
  ".mypy_cache"
  ".tox"
  ".eggs"
  "dist"
  "build"
  ".idea"
  ".vscode"
)

# -----------------------------
# File patterns to include
# (meaningful source files)
# -----------------------------
INCLUDE_NAMES=(
  "*.py"
  "*.html" "*.htm"
  "*.css" "*.scss" "*.sass" "*.less"
  "*.js" "*.jsx" "*.mjs" "*.cjs"
  "*.ts" "*.tsx"
  "*.json"
  "*.yml" "*.yaml"
  "*.toml"
  "*.ini" "*.cfg"
  "*.md" "*.mdx"
  "*.sh"

  "Dockerfile"
  "docker-compose.yml" "docker-compose.yaml"
  "Makefile"
  "Procfile"
  "manage.py"
  "wsgi.py" "asgi.py"
  "tailwind.config.js" "postcss.config.js"
  "package.json"
  "requirements.txt" "requirements*.txt"
  "pyproject.toml"
  "setup.cfg"
)

# -----------------------------
# Exclude specific filenames/patterns
# (generated, noisy, duplicates)
# -----------------------------
EXCLUDE_NAMES=(
  "*.min.js"
  "*.map"
  "*.lock"
  "package-lock.json"
  "yarn.lock"
  "pnpm-lock.yaml"
  ".env"
  ".env.*"
  "*.sqlite3"
  "*.db"
  "*.log"
  "staticfiles.json"
)

# -----------------------------
# Exclude by extension (binary/media/fonts)
# -----------------------------
EXCLUDE_EXTS=(
  "png" "jpg" "jpeg" "gif" "webp" "ico" "svg"
  "mp4" "mov" "webm" "mp3" "wav"
  "pdf" "zip" "tar" "gz" "bz2" "7z"
  "woff" "woff2" "ttf" "otf" "eot"
)

# -----------------------------
# Exclude by path substring (vendored trees)
# Even if they sneak in via config/static etc.
# -----------------------------
EXCLUDE_PATH_CONTAINS=(
  "/wagtailadmin/"
  "/django-admin/"
  "/admin/"
  "/vendor/"
  "/select2/"
  "/xregexp/"
  "/coloris/"
)

# Build prune expr
PRUNE_EXPR=()
for d in "${PRUNE_DIRS[@]}"; do
  PRUNE_EXPR+=( -name "$d" -o )
done
unset 'PRUNE_EXPR[${#PRUNE_EXPR[@]}-1]' 2>/dev/null || true

# Build include expr
INCLUDE_EXPR=()
for p in "${INCLUDE_NAMES[@]}"; do
  INCLUDE_EXPR+=( -name "$p" -o )
done
unset 'INCLUDE_EXPR[${#INCLUDE_EXPR[@]}-1]' 2>/dev/null || true

# Build exclude name expr
EXCLUDE_NAME_EXPR=()
for p in "${EXCLUDE_NAMES[@]}"; do
  EXCLUDE_NAME_EXPR+=( ! -name "$p" )
done

# Build exclude ext expr
EXCLUDE_EXT_EXPR=()
for ext in "${EXCLUDE_EXTS[@]}"; do
  EXCLUDE_EXT_EXPR+=( ! -iname "*.${ext}" )
done

# Helper: returns 0 if path should be excluded by substring list
should_exclude_path() {
  local f="$1"
  for needle in "${EXCLUDE_PATH_CONTAINS[@]}"; do
    if [[ "$f" == *"$needle"* ]]; then
      return 0
    fi
  done
  return 1
}

# Helper: filter out hashed duplicates like app.a759eb1db7ba.css
# Matches: .<8+ hex>.(css|js|svg|...)
is_hashed_asset() {
  local f="$1"
  # adjust if you want stricter/looser
  if [[ "$f" =~ \.[a-f0-9]{8,}\.[a-zA-Z0-9]+$ ]]; then
    return 0
  fi
  return 1
}

# Use -print0 to safely handle weird file names
find . \
  \( -type d \( "${PRUNE_EXPR[@]}" \) -prune \) -o \
  \( -type f \( "${INCLUDE_EXPR[@]}" \) \
     "${EXCLUDE_NAME_EXPR[@]}" \
     "${EXCLUDE_EXT_EXPR[@]}" \
     -print0 \
  \) \
| sort -z \
| while IFS= read -r -d '' f; do
    # Drop vendored paths
    if should_exclude_path "$f"; then
      continue
    fi

    # Drop hashed duplicates
    if is_hashed_asset "$f"; then
      continue
    fi

    {
      printf "\n=== File: %s ===\n" "$f"

      if command -v stat >/dev/null 2>&1; then
        if stat --version >/dev/null 2>&1; then
          stat -c "=== Size: %s bytes | Modified: %y ===" "$f" || true
        else
          stat -f "=== Size: %z bytes | Modified: %Sm ===" "$f" || true
        fi
        printf "\n"
      fi

      # Keep output readable if file has weird bytes
      if command -v iconv >/dev/null 2>&1; then
        iconv -f utf-8 -t utf-8 -c "$f" || cat "$f"
      else
        cat "$f"
      fi

      printf "\n"
    } >> "$OUTFILE"
  done

echo "Done. Files: $(grep -c '^=== File:' "$OUTFILE" || true) | Lines: $(wc -l < "$OUTFILE")" >&2
