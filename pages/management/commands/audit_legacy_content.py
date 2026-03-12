from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from pages.models import HomePage, MenuSectionPage, TreatmentPage


class Command(BaseCommand):
    help = "Audit legacy page content and link integrity debt."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--fail-on-issues", action="store_true")

    def _legacy_block_count(self) -> int:
        count = 0
        for page in HomePage.objects.all():
            raw = page.sections.raw_data if page.sections else []
            for block in raw:
                block_type = block.get("type")
                value = block.get("value") or {}
                if block_type == "featured_menu":
                    count += 1
                if block_type == "hero" and value.get("hero_images"):
                    count += 1
                if block_type == "text_image" and value.get("image") and not value.get("media"):
                    count += 1
        return count

    def handle(self, *args, **options):
        report = {
            "legacy_blocks": self._legacy_block_count(),
            "menu_sections_without_treatment": MenuSectionPage.objects.filter(treatment__isnull=True).count(),
            "treatment_pages_without_option": TreatmentPage.objects.filter(option__isnull=True).count(),
        }
        issues_total = sum(report.values())
        report["issues_total"] = issues_total

        if options["as_json"]:
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        else:
            for key, value in report.items():
                self.stdout.write(f"{key}: {value}")

        if options["fail_on_issues"] and issues_total:
            raise SystemExit(1)
