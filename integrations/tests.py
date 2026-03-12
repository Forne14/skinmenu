from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.test import TestCase, override_settings

from integrations.leads import enqueue_newsletter_signup, process_outbound_event
from integrations.models import OutboundEvent


class LeadSyncTests(TestCase):
    @override_settings(LEAD_SYNC_ENABLED=False)
    def test_enqueue_newsletter_signup_creates_pending_event(self):
        enqueue_newsletter_signup({"email": "hello@example.com"})
        event = OutboundEvent.objects.get()
        self.assertEqual(event.status, OutboundEvent.STATUS_PENDING)
        self.assertEqual(event.destination, "noop")

    @override_settings(LEAD_SYNC_ENABLED=False)
    def test_newsletter_idempotency_prevents_duplicate_events(self):
        payload = {"email": "hello@example.com", "source_url": "/contact/"}
        enqueue_newsletter_signup(payload)
        enqueue_newsletter_signup(payload)
        self.assertEqual(OutboundEvent.objects.count(), 1)

    @override_settings(
        LEAD_SYNC_ENABLED=True,
        LEAD_SYNC_BACKEND="webhook",
        LEAD_SYNC_WEBHOOK_URL="https://example.test/webhook",
        LEAD_SYNC_MAX_ATTEMPTS=2,
    )
    @patch("integrations.leads._schedule_retry")
    @patch("integrations.leads.WebhookLeadSyncAdapter.send", side_effect=RuntimeError("boom"))
    def test_process_outbound_event_moves_to_dead_letter_after_max_attempts(self, _send, _schedule_retry):
        event = OutboundEvent.objects.create(
            event_type=OutboundEvent.EVENT_NEWSLETTER_SIGNUP,
            idempotency_key="x" * 64,
            payload={"email": "hello@example.com"},
            status=OutboundEvent.STATUS_PENDING,
        )
        process_outbound_event(event.id)
        event.refresh_from_db()
        self.assertEqual(event.status, OutboundEvent.STATUS_FAILED)

        process_outbound_event(event.id)
        event.refresh_from_db()
        self.assertEqual(event.status, OutboundEvent.STATUS_DEAD_LETTER)


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


class AdminOutboundEventsViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    def test_outbound_events_view_renders(self):
        OutboundEvent.objects.create(
            event_type=OutboundEvent.EVENT_NEWSLETTER_SIGNUP,
            idempotency_key="view-test-key",
            payload={"email": "hello@example.com"},
        )
        response = self.client.get(reverse("integrations_outbound_events"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Outbound Integration Events")
