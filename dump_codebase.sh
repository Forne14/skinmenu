#!/usr/bin/env bash
set -euo pipefail

# Dump a Django/Wagtail codebase into a single text file.
# Usage:
#   ./dump_codebase.sh
#   ./dump_codebase.sh -o codebase-django.txt
#   ./dump_codebase.sh -o /tmp/dump.txt
#
# Run from the repository root.

OUTFILE="codebase-django.txt"

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

# Directories to prune (ignored entirely)
PRUNE_DIRS=(
  ".git"
  "venv" ".venv"
  "__pycache__"
  "node_modules"
  "media"
  "staticfiles"
  ".mypy_cache"
  ".pytest_cache"
  ".ruff_cache"
  ".tox"
  ".eggs"
  "dist"
  "build"
  ".cache"
  ".idea"
  ".vscode"
)

# File patterns to include (relevant code/config/docs)
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
  "*.md" "*.mdx" "*.txt"
  "*.sh"
  "*.env.example" "*.env.sample"
  "Dockerfile" "docker-compose.yml" "docker-compose.yaml"
  "Makefile"
  "Procfile"
  "nginx.conf" "*.nginx" "*.conf"
  "requirements.txt" "requirements*.txt"
  "Pipfile" "Pipfile.lock"
  "pyproject.toml"
  "setup.cfg"
  "manage.py"
  "wsgi.py" "asgi.py"
  "tailwind.config.js" "postcss.config.js"
  "package.json"
)

# File patterns to exclude even if they match an include
EXCLUDE_NAMES=(
  "package-lock.json"
  "yarn.lock"
  "pnpm-lock.yaml"
  "*.min.js"
  "*.map"
  ".env"
  ".env.*"
  "*.sqlite3"
  "*.db"
  "*.log"
)

# Exclude by extension (binary/media/fonts)
EXCLUDE_EXTS=(
  "png" "jpg" "jpeg" "gif" "webp" "ico"
  "mp4" "mov" "webm" "mp3" "wav"
  "pdf" "zip" "tar" "gz" "bz2" "7z"
  "woff" "woff2" "ttf" "otf" "eot" "sh" "txt"
)

# Build the prune expression for find
PRUNE_EXPR=()
for d in "${PRUNE_DIRS[@]}"; do
  PRUNE_EXPR+=( -name "$d" -o )
done
unset 'PRUNE_EXPR[${#PRUNE_EXPR[@]}-1]' 2>/dev/null || true

# Build include expression
INCLUDE_EXPR=()
for p in "${INCLUDE_NAMES[@]}"; do
  INCLUDE_EXPR+=( -name "$p" -o )
done
unset 'INCLUDE_EXPR[${#INCLUDE_EXPR[@]}-1]' 2>/dev/null || true

# Build exclude-name expression
EXCLUDE_NAME_EXPR=()
for p in "${EXCLUDE_NAMES[@]}"; do
  EXCLUDE_NAME_EXPR+=( ! -name "$p" )
done

# Build exclude extension expression
EXCLUDE_EXT_EXPR=()
for ext in "${EXCLUDE_EXTS[@]}"; do
  EXCLUDE_EXT_EXPR+=( ! -iname "*.${ext}" )
done

echo "Writing dump to: $OUTFILE" >&2

# Use -print0 to handle spaces/newlines in file names safely
find . \
  \( -type d \( "${PRUNE_EXPR[@]}" \) -prune \) -o \
  \( -type f \( "${INCLUDE_EXPR[@]}" \) \
     "${EXCLUDE_NAME_EXPR[@]}" \
     "${EXCLUDE_EXT_EXPR[@]}" \
     -print0 \
  \) \
| sort -z \
| while IFS= read -r -d '' f; do
    {
      printf "\n=== File: %s ===\n" "$f"

      # Helpful: show size, but don't depend on GNU stat formatting differences too much.
      if command -v stat >/dev/null 2>&1; then
        if stat --version >/dev/null 2>&1; then
          # GNU stat
          stat -c "=== Size: %s bytes | Modified: %y ===" "$f" || true
        else
          # BSD/macOS stat
          stat -f "=== Size: %z bytes | Modified: %Sm ===" "$f" || true
        fi
        printf "\n"
      fi

      # If file has non-UTF8 bytes, strip them so the dump stays readable
      # (iconv is common on macOS/Linux; if missing, just cat).
      if command -v iconv >/dev/null 2>&1; then
        iconv -f utf-8 -t utf-8 -c "$f" || cat "$f"
      else
        cat "$f"
      fi

      printf "\n"
    } >> "$OUTFILE"
  done

echo "Done. Lines: $(wc -l < "$OUTFILE")" >&2
