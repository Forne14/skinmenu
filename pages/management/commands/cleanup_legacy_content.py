from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from pages.models import HomePage


class Command(BaseCommand):
    help = "Cleanup safe legacy structures in homepage StreamField content."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Persist cleanup changes.")

    def _clean_blocks(self, blocks: list[dict]) -> tuple[list[dict], int]:
        cleaned: list[dict] = []
        changes = 0

        for block in blocks:
            block_type = block.get("type")
            value = block.get("value") or {}

            # Remove empty legacy featured block.
            if block_type == "featured_menu":
                featured = value.get("featured_pages") or []
                cta_page = value.get("cta_page")
                intro = (value.get("intro") or "").strip()
                if not featured and not cta_page and not intro:
                    changes += 1
                    continue

            # If modern hero_media exists, drop hero_images fallback to reduce dual-source drift.
            if block_type == "hero" and value.get("hero_media") and value.get("hero_images"):
                value = dict(value)
                value["hero_images"] = []
                block = dict(block)
                block["value"] = value
                changes += 1

            cleaned.append(block)

        return cleaned, changes

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        total_changes = 0
        touched = 0

        qs = HomePage.objects.all()
        with transaction.atomic():
            for page in qs:
                blocks = page.sections.raw_data if page.sections else []
                cleaned, changes = self._clean_blocks(blocks)
                if not changes:
                    continue
                total_changes += changes
                touched += 1
                self.stdout.write(f"page={page.id} changes={changes}")
                if apply:
                    page.sections = cleaned
                    page.save(update_fields=["sections"])

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(f"mode={'apply' if apply else 'dry-run'} pages_touched={touched} changes={total_changes}")
