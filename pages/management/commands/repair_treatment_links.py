from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Treatment, TreatmentOption
from pages.models import TreatmentPage

class Command(BaseCommand):
    help = "Repairs unlinked TreatmentPage records on production by re-creating missing snippets."

    @transaction.atomic
    def handle(self, *args, **options):
        pages = TreatmentPage.objects.all()
        self.stdout.write(f"Found {pages.count()} TreatmentPages.")

        for page in pages:
            # We assume for now that each Page should have a corresponding top-level Treatment snippet.
            # If the page was meant to be an Option, the editor can adjust it later, 
            # but this will at least restore content visibility.
            
            treatment, created = Treatment.objects.get_or_create(
                slug=page.slug,
                defaults={
                    "name": page.title,
                    "summary": page.summary if hasattr(page, 'summary') else "",
                    "is_active": True,
                }
            )
            
            if created:
                self.stdout.write(f"Created Treatment snippet for: {page.title}")
            
            if page.treatment_id != treatment.id:
                page.treatment = treatment
                page.save_revision().publish()
                self.stdout.write(f"Linked Page '{page.title}' to Treatment '{treatment.name}'")

        self.stdout.write(self.style.SUCCESS("Successfully repaired treatment links."))
