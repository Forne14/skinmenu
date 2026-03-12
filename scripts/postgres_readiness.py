#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


def main() -> int:
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("DATABASE_URL is not set. Current environment will use sqlite.")
        return 0

    parsed = urlparse(db_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        print("DATABASE_URL is set but not postgres/postgresql.")
        return 1

    missing = []
    if not parsed.hostname:
        missing.append("hostname")
    if not parsed.path or parsed.path == "/":
        missing.append("database name")
    if missing:
        print("DATABASE_URL missing:", ", ".join(missing))
        return 1

    print("postgres_readiness: url shape ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

