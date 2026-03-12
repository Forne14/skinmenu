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

        if getattr(settings, "USE_S3_STORAGE", False):
            if "storages" not in settings.INSTALLED_APPS:
                issues.append("USE_S3_STORAGE requires 'storages' in INSTALLED_APPS")
            if not getattr(settings, "MEDIA_URL", "").startswith("http"):
                issues.append("USE_S3_STORAGE expects MEDIA_URL to be absolute (http/https)")
            default_storage = settings.STORAGES.get("default", {})
            opts = default_storage.get("OPTIONS", {})
            if not opts.get("bucket_name"):
                issues.append("USE_S3_STORAGE requires AWS_STORAGE_BUCKET_NAME")
            if not (opts.get("endpoint_url") or opts.get("region_name")):
                issues.append("USE_S3_STORAGE requires AWS_S3_ENDPOINT_URL or AWS_S3_REGION_NAME")

        if issues:
            for issue in issues:
                self.stdout.write(self.style.ERROR(issue))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("integration_config_ok"))
