#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8001}"
APP_HOST_ALIAS="${APP_HOST_ALIAS:-skinmenu.local}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if ! grep -Eq "(^|[[:space:]])${APP_HOST_ALIAS}([[:space:]]|$)" /etc/hosts; then
  cat <<EOF
[skinmenu] Host alias '${APP_HOST_ALIAS}' is not in /etc/hosts.
[skinmenu] Add it once:
  echo '127.0.0.1 ${APP_HOST_ALIAS}' | sudo tee -a /etc/hosts
EOF
fi

echo "[skinmenu] Starting dev server on http://${HOST}:${PORT}/"
echo "[skinmenu] Preferred URL: http://${APP_HOST_ALIAS}:${PORT}/"

exec python manage.py runserver "${HOST}:${PORT}"
