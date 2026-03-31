from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Treatment, TreatmentOption
from pages.models import TreatmentPage

class Command(BaseCommand):
    help = "Repairs unlinked TreatmentPage records on production by linking to available Treatments or Options."

    @transaction.atomic
    def handle(self, *args, **options):
        pages = TreatmentPage.objects.all()
        self.stdout.write(f"Found {pages.count()} TreatmentPages.")

        for page in pages:
            # 1. Try to find a specific Option first (since Options hold the Prices/Facts)
            option = TreatmentOption.objects.filter(treatment__slug=page.slug).first()
            if not option:
                # Try by option name if slug doesn't match
                option = TreatmentOption.objects.filter(name__icontains=page.title).first()

            if option:
                page.option = option
                page.treatment = option.treatment
                page.save_revision().publish()
                self.stdout.write(f"Linked Page '{page.title}' to Option '{option.name}' and Treatment '{option.treatment.name}'")
                continue

            # 2. Fallback to top-level Treatment if no specific option found
            treatment = Treatment.objects.filter(slug=page.slug).first()
            if not treatment:
                treatment = Treatment.objects.filter(name__icontains=page.title).first()
            
            if treatment:
                page.treatment = treatment
                page.save_revision().publish()
                self.stdout.write(f"Linked Page '{page.title}' to Treatment '{treatment.name}'")
            else:
                self.stdout.write(self.style.WARNING(f"Could not find matching Treatment or Option for: {page.title}"))

        self.stdout.write(self.style.SUCCESS("Successfully repaired treatment links."))
