from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Validate integration configuration invariants."

    def handle(self, *args, **options):
        issues: list[str] = []

        if settings.LEAD_SYNC_ENABLED and settings.LEAD_SYNC_BACKEND == "webhook" and not settings.LEAD_SYNC_WEBHOOK_URL:
            issues.append("LEAD_SYNC_WEBHOOK_URL missing for webhook backend")

        if settings.LEAD_SYNC_TIMEOUT_SECONDS <= 0:
            issues.append("LEAD_SYNC_TIMEOUT_SECONDS must be > 0")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.ERROR(issue))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("integration_config_ok"))

