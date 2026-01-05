#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import subprocess
from pathlib import Path


def _project_root() -> Path:
    # scripts/smoke_test.py -> repo root is parent of "scripts"
    return Path(__file__).resolve().parents[1]


def _add_project_to_syspath() -> None:
    root = str(_project_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def _curl(url: str) -> tuple[int, str]:
    """
    Returns: (exit_code, stdout)
    Uses curl because it mirrors the server+nginx reality well.
    """
    p = subprocess.run(
        ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", url],
        text=True,
        capture_output=True,
    )
    # stdout contains status code if curl succeeded
    return p.returncode, (p.stdout or "").strip()


def main() -> int:
    _add_project_to_syspath()

    # Prefer env, but provide a safe default
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.production"))

    import django  # noqa: E402
    from django.conf import settings  # noqa: E402
    from django.test import Client  # noqa: E402

    django.setup()

    print("== Smoke: Django import + setup OK ==")
    print("DJANGO_SETTINGS_MODULE =", os.environ.get("DJANGO_SETTINGS_MODULE"))
    print("DEBUG =", getattr(settings, "DEBUG", None))

    # --- App-level check (no nginx involved)
    c = Client(HTTP_HOST="skin-menu.co.uk", wsgi_url_scheme="https")
    r = c.get("/admin/login/")
    print("Django Client GET /admin/login/ ->", r.status_code)
    if r.status_code != 200:
        print(r.content[:500])
        return 2

    # --- Static manifest sanity
    static_root = Path(getattr(settings, "STATIC_ROOT", "")) if getattr(settings, "STATIC_ROOT", None) else None
    if not static_root:
        print("ERROR: STATIC_ROOT is not set")
        return 3

    manifest_path = static_root / "staticfiles.json"
    if not manifest_path.exists():
        print(f"ERROR: manifest missing: {manifest_path}")
        return 4

    print("manifest ok:", manifest_path)

    # Try to request a real hashed static path from nginx (most reliable proof)
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as e:
        print("ERROR: failed reading staticfiles.json:", e)
        return 5

    # This key commonly exists; if not, fall back to any file in the manifest
    key = "admin/css/base.css"
    target = manifest.get(key)
    if not target:
        # Try to find a reasonable admin asset
        for k, v in manifest.items():
            if isinstance(k, str) and k.startswith("admin/") and isinstance(v, str) and v.endswith(".css"):
                key, target = k, v
                break

    if not target:
        # Last resort: pick any manifest entry
        for k, v in manifest.items():
            if isinstance(k, str) and isinstance(v, str):
                key, target = k, v
                break

    if not target:
        print("ERROR: manifest has no usable entries")
        return 6

    url = f"http://127.0.0.1/static/{target}"
    rc, code = _curl(url)
    print(f"curl {url} -> rc={rc} http={code} (manifest key={key})")

    if rc != 0:
        print("ERROR: curl failed (is curl installed? is nginx running?)")
        return 7

    # If nginx isn't set up for /static/, you'll usually see 404 here
    if code != "200":
        print("ERROR: nginx did not serve static correctly (expected 200).")
        print("This usually means nginx lacks: location /static/ { alias .../staticfiles/; }")
        return 8

    print("== Smoke: OK ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
