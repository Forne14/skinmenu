from __future__ import annotations

from django.core.management.base import BaseCommand

from catalog.models import (
    TreatmentFAQ,
    TreatmentMedia,
    TreatmentOptionContentBlock,
    TreatmentOptionFact,
    TreatmentPrice,
    TreatmentStep,
)
from pages.models import MenuSectionPage, TreatmentPage


class Command(BaseCommand):
    help = "Audit content integrity for treatment-linked content and page links."

    def handle(self, *args, **options):
        checks = [
            ("orphan_treatment_option_facts", TreatmentOptionFact.objects.filter(option__isnull=True).count()),
            ("orphan_treatment_prices", TreatmentPrice.objects.filter(option__isnull=True).count()),
            ("orphan_treatment_media", TreatmentMedia.objects.filter(option__isnull=True).count()),
            ("orphan_treatment_faqs", TreatmentFAQ.objects.filter(option__isnull=True).count()),
            ("orphan_treatment_steps", TreatmentStep.objects.filter(option__isnull=True).count()),
            (
                "orphan_treatment_option_content_blocks",
                TreatmentOptionContentBlock.objects.filter(option__isnull=True).count(),
            ),
            ("menu_sections_without_treatment", MenuSectionPage.objects.filter(treatment__isnull=True).count()),
            ("treatment_pages_without_option", TreatmentPage.objects.filter(option__isnull=True).count()),
        ]

        total_issues = 0
        for key, count in checks:
            total_issues += count
            self.stdout.write(f"{key}: {count}")

        if total_issues:
            self.stdout.write(self.style.WARNING(f"integrity_issues_total: {total_issues}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("integrity_issues_total: 0"))
