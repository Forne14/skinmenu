#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


def _project_root() -> Path:
    # scripts/smoke_test.py -> repo root is parent of "scripts"
    return Path(__file__).resolve().parents[1]


def _add_project_to_syspath() -> None:
    root = str(_project_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def _curl(args: List[str]) -> Tuple[int, str, str]:
    """
    Returns: (exit_code, stdout, stderr)

    We use curl because it mirrors the server+nginx reality well.
    Caller should include:
      - "-sS", "-o", "/dev/null", "-w", "%{http_code}"
    """
    p = subprocess.run(args, text=True, capture_output=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _determine_static_probe_host() -> str:
    """
    Pick the hostname we expect nginx to serve for.

    Priority:
      1) SMOKE_HOST env
      2) settings.ALLOWED_HOSTS first non-wildcard
      3) default to skin-menu.co.uk
    """
    env_host = os.environ.get("SMOKE_HOST")
    if env_host:
        return env_host.strip()

    try:
        from django.conf import settings  # noqa: E402

        allowed = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
        for h in allowed:
            if isinstance(h, str) and h and h not in ("*", "0.0.0.0", "127.0.0.1", "localhost"):
                return h
    except Exception:
        pass

    return "skin-menu.co.uk"


def main() -> int:
    _add_project_to_syspath()

    # Prefer env, but provide a safe default
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.production"),
    )

    import django  # noqa: E402

    django.setup()

    from django.conf import settings  # noqa: E402
    from django.test import Client  # noqa: E402

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

    host = _determine_static_probe_host()
    path = f"/static/{target}"

    # We want to verify nginx serves /static correctly.
    #
    # IMPORTANT:
    # - Curling https://127.0.0.1 without Host/SNI can hit the wrong vhost and produce 502.
    # - Best check: curl the real host (domain) OR hit 127.0.0.1 but force Host header and SNI.
    #
    # We'll attempt in order:
    #  1) https://{host}{path}  (normal real-world)
    #  2) https://127.0.0.1{path} with Host header = host, and --resolve for SNI/cert routing
    #  3) http://127.0.0.1{path} with Host header = host (if local http->https redirect exists it may return 301)
    #
    attempts: List[Tuple[str, List[str], str]] = []

    # 1) domain directly (best)
    url1 = f"https://{host}{path}"
    attempts.append(
        (
            "domain_https",
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", url1],
            url1,
        )
    )

    # 2) 127.0.0.1 but force Host + SNI via --resolve; -k to skip cert mismatch if any
    # --resolve makes curl send SNI/Host = host while connecting to 127.0.0.1
    url2 = f"https://{host}{path}"
    attempts.append(
        (
            "loopback_https_resolve",
            ["curl", "-sS", "-k", "--resolve", f"{host}:443:127.0.0.1", "-o", "/dev/null", "-w", "%{http_code}", url2],
            f"https://127.0.0.1{path} (SNI/Host={host})",
        )
    )

    # 3) http loopback with Host header (some setups 301 to https; acceptable)
    url3 = f"http://127.0.0.1{path}"
    attempts.append(
        (
            "loopback_http_host",
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-H", f"Host: {host}", url3],
            f"{url3} (Host={host})",
        )
    )

    ok = False
    for label, cmd, display_url in attempts:
        rc, code, err = _curl(cmd)
        print(f"curl[{label}] {display_url} -> rc={rc} http={code} (manifest key={key})")
        if rc == 0 and code == "200":
            ok = True
            break

        # Some setups intentionally redirect http->https; allow 301 for the http attempt,
        # but don't treat it as success by itself (since it doesn't prove file served).
        if label == "loopback_http_host" and rc == 0 and code in ("301", "302"):
            print("note: http redirect observed (expected on many setups). continuing...")

        if err:
            print(f"curl[{label}] stderr:", err)

    if not ok:
        print("ERROR: nginx did not serve static correctly (expected 200).")
        print("Hints:")
        print(" - Ensure nginx site has: location /static/ { alias /home/deploy/apps/skinmenu/staticfiles/; }")
        print(" - Ensure you're testing the correct vhost (Host header / SNI matters).")
        print(" - If using /home/deploy paths, ensure nginx can traverse parent directories (execute bit / ACL).")
        return 8

    print("== Smoke: OK ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
