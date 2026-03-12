from django.core.management.base import BaseCommand

from integrations.leads import process_outbound_event
from integrations.models import OutboundEvent


class Command(BaseCommand):
    help = "Replay failed/pending outbound events for lead sync."

    def add_arguments(self, parser):
        parser.add_argument("--status", default="failed,pending")
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        statuses = [s.strip() for s in options["status"].split(",") if s.strip()]
        limit = int(options["limit"])
        qs = OutboundEvent.objects.filter(status__in=statuses).order_by("created_at")[:limit]
        count = 0
        for event in qs:
            try:
                process_outbound_event(event.id)
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.WARNING(f"event_id={event.id} failed: {exc}"))
            else:
                count += 1
                self.stdout.write(self.style.SUCCESS(f"event_id={event.id} sent"))
        self.stdout.write(f"processed={count}")

