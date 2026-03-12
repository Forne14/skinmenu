from io import StringIO

from django.core.management import call_command
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


class ValidateIntegrationsConfigTests(TestCase):
    @override_settings(
        LEAD_SYNC_ENABLED=True,
        LEAD_SYNC_BACKEND="webhook",
        LEAD_SYNC_WEBHOOK_URL="",
    )
    def test_validate_integrations_config_fails_when_webhook_missing(self):
        with self.assertRaises(SystemExit):
            call_command("validate_integrations_config", stdout=StringIO())

    @override_settings(LEAD_SYNC_ENABLED=False)
    def test_validate_integrations_config_passes_defaults(self):
        out = StringIO()
        call_command("validate_integrations_config", stdout=out)
        self.assertIn("integration_config_ok", out.getvalue())
