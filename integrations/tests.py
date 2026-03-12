from django.test import TestCase, override_settings

from integrations.leads import enqueue_newsletter_signup
from integrations.models import OutboundEvent


class LeadSyncTests(TestCase):
    @override_settings(LEAD_SYNC_ENABLED=False)
    def test_enqueue_newsletter_signup_creates_pending_event(self):
        enqueue_newsletter_signup({"email": "hello@example.com"})
        event = OutboundEvent.objects.get()
        self.assertEqual(event.status, OutboundEvent.STATUS_PENDING)
        self.assertEqual(event.destination, "noop")

