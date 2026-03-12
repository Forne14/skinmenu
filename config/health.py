from __future__ import annotations

from django.core.cache import caches
from django.db import connection
from django.http import JsonResponse


def healthz(request):
    checks: dict[str, str] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "error"

    try:
        cache = caches["default"]
        cache.set("healthz", "ok", timeout=5)
        checks["cache"] = "ok" if cache.get("healthz") == "ok" else "error"
    except Exception:  # noqa: BLE001
        checks["cache"] = "error"

    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JsonResponse({"status": "ok" if status_code == 200 else "degraded", "checks": checks}, status=status_code)

