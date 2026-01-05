import os
import sys
import subprocess
import django
from django.test import Client

def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    # Django-level smoke test (no network)
    django.setup()
    c = Client(HTTP_HOST="www.skin-menu.co.uk", wsgi_url_scheme="https")
    r = c.get("/admin/login/")
    print("Django test client /admin/login/:", r.status_code)
    if r.status_code != 200:
        print("Expected 200, got", r.status_code, file=sys.stderr)
        return 2

    # Nginx-level smoke test (real HTTP request)
    # This catches nginx alias mistakes, TLS issues, upstream socket issues, etc.
    try:
        subprocess.run(
            ["curl", "-fsS", "https://www.skin-menu.co.uk/admin/login/"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            timeout=15,
        )
        print("curl https://www.skin-menu.co.uk/admin/login/: ok")
    except Exception as e:
        print("curl failed:", e, file=sys.stderr)
        return 3

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
