from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db import connection


CRITICAL_TABLES = [
    "auth_user",
    "wagtailcore_page",
    "wagtailcore_site",
    "wagtailimages_image",
    "wagtaildocs_document",
    "pages_homepage",
    "pages_treatmentsindexpage",
    "pages_menusectionpage",
    "pages_treatmentpage",
    "pages_blogpage",
    "pages_contactpage",
    "site_settings_globalsitesettings",
    "site_settings_navigationsettings",
    "site_settings_analyticssettings",
    "catalog_treatment",
    "catalog_treatmentoption",
    "catalog_treatmentprice",
    "wagtailforms_formsubmission",
    "integrations_outboundevent",
]


@dataclass
class TableSnapshot:
    count: int
    max_id: int
    edge_hash: str

    def as_dict(self) -> dict[str, int | str]:
        return {
            "count": self.count,
            "max_id": self.max_id,
            "edge_hash": self.edge_hash,
        }


def _edge_hash_for_table(table_name: str) -> str:
    # Hash first + last id windows to catch obvious truncation/reorder mistakes.
    # This is not a full checksum, but it's cheap and cross-database.
    pk_col = connection.introspection.get_primary_key_column(connection.cursor(), table_name)
    if not pk_col:
        return hashlib.sha256(b"no-primary-key").hexdigest()

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {pk_col} FROM {table_name} ORDER BY {pk_col} ASC LIMIT 200")
        head = [row[0] for row in cursor.fetchall()]
        cursor.execute(f"SELECT {pk_col} FROM {table_name} ORDER BY {pk_col} DESC LIMIT 200")
        tail = [row[0] for row in cursor.fetchall()]
    payload = {"head": head, "tail": tail}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _snapshot_table(table_name: str) -> TableSnapshot:
    pk_col = connection.introspection.get_primary_key_column(connection.cursor(), table_name)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = int(cursor.fetchone()[0] or 0)
        if pk_col:
            cursor.execute(f"SELECT COALESCE(MAX({pk_col}), 0) FROM {table_name}")
            max_id = int(cursor.fetchone()[0] or 0)
        else:
            max_id = 0
    edge_hash = _edge_hash_for_table(table_name)
    return TableSnapshot(count=count, max_id=max_id, edge_hash=edge_hash)


class Command(BaseCommand):
    help = "Create a deterministic database snapshot manifest for migration parity checks."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="", help="Write JSON snapshot to this file path.")
        parser.add_argument(
            "--tables",
            default="",
            help="Optional comma-separated table list. Defaults to project critical tables.",
        )

    def handle(self, *args, **options):
        output_path = (options.get("output") or "").strip()
        raw_tables = (options.get("tables") or "").strip()
        if raw_tables:
            wanted_tables = [t.strip() for t in raw_tables.split(",") if t.strip()]
        else:
            wanted_tables = CRITICAL_TABLES

        existing = set(connection.introspection.table_names())
        tables = [t for t in wanted_tables if t in existing]

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database_vendor": connection.vendor,
            "database_name": str(connection.settings_dict.get("NAME", "")),
            "tables": {table: _snapshot_table(table).as_dict() for table in tables},
        }

        payload = json.dumps(report, indent=2, sort_keys=True)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(payload)
            self.stdout.write(self.style.SUCCESS(f"snapshot_written={output_path} tables={len(tables)}"))
            return

        self.stdout.write(payload)
