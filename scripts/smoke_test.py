import os
import django
from django.test import Client

def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

    host = os.environ.get("SMOKE_TEST_HOST", "skin-menu.co.uk")
    scheme = os.environ.get("SMOKE_TEST_SCHEME", "https")

    c = Client(HTTP_HOST=host, wsgi_url_scheme=scheme)

    r = c.get("/admin/login/")
    print("admin/login status:", r.status_code)
    assert r.status_code == 200, f"/admin/login returned {r.status_code}"

if __name__ == "__main__":
    main()
