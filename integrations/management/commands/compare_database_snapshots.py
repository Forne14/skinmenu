from __future__ import annotations

import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compare two database snapshot JSON files and fail on parity mismatches."

    def add_arguments(self, parser):
        parser.add_argument("--left", required=True, help="Path to baseline snapshot JSON.")
        parser.add_argument("--right", required=True, help="Path to candidate snapshot JSON.")

    def handle(self, *args, **options):
        left_path = options["left"]
        right_path = options["right"]

        with open(left_path, "r", encoding="utf-8") as handle:
            left = json.load(handle)
        with open(right_path, "r", encoding="utf-8") as handle:
            right = json.load(handle)

        left_tables = left.get("tables", {})
        right_tables = right.get("tables", {})
        shared = sorted(set(left_tables.keys()) & set(right_tables.keys()))
        only_left = sorted(set(left_tables.keys()) - set(right_tables.keys()))
        only_right = sorted(set(right_tables.keys()) - set(left_tables.keys()))

        mismatches: list[str] = []
        if only_left:
            mismatches.append(f"missing_in_right={','.join(only_left)}")
        if only_right:
            mismatches.append(f"extra_in_right={','.join(only_right)}")

        for table in shared:
            l = left_tables[table]
            r = right_tables[table]
            for key in ("count", "max_id", "edge_hash"):
                if l.get(key) != r.get(key):
                    mismatches.append(
                        f"{table}.{key}: left={l.get(key)} right={r.get(key)}"
                    )

        if mismatches:
            for line in mismatches:
                self.stdout.write(self.style.ERROR(line))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("database_snapshots_match"))

