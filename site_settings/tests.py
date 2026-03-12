import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.urls import reverse

from integrations.models import OutboundEvent


@override_settings(NEWSLETTER_CSV_PATH=Path(tempfile.gettempdir()) / "skinmenu-newsletter-test.csv")
class NewsletterSubscribeTests(TestCase):
    def setUp(self):
        self.url = reverse("newsletter_subscribe")
        self.csv_path = Path(tempfile.gettempdir()) / "skinmenu-newsletter-test.csv"
        if self.csv_path.exists():
            self.csv_path.unlink()

    def tearDown(self):
        if self.csv_path.exists():
            self.csv_path.unlink()

    def test_rejects_non_post(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_rejects_invalid_email_and_redirects_with_error_query(self):
        response = self.client.post(
            self.url,
            {"email": "not-an-email"},
            HTTP_REFERER="http://testserver/contact/",
        )
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response["Location"])
        self.assertEqual(parsed.path, "/contact/")
        query = parse_qs(parsed.query)
        self.assertEqual(query["newsletter"], ["error"])
        self.assertEqual(query["newsletter_message"], ["Invalid email."])

    def test_success_writes_csv_and_redirects_with_success_query(self):
        response = self.client.post(
            self.url,
            {
                "email": "hello@example.com",
                "source_url": "https://skin-menu.co.uk/?utm=ig",
                "consent_analytics": "1",
            },
            HTTP_REFERER="http://testserver/",
        )
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response["Location"])
        query = parse_qs(parsed.query)
        self.assertEqual(query["newsletter"], ["success"])
        self.assertEqual(query["newsletter_message"], ["Thanks for subscribing."])

        self.assertTrue(self.csv_path.exists())
        rows = [line.strip() for line in self.csv_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(rows[0], "email,submitted_at,source_url")
        self.assertIn("hello@example.com", rows[1])
        self.assertIn("https://skin-menu.co.uk/?utm=ig", rows[1])
        self.assertEqual(OutboundEvent.objects.filter(event_type="newsletter_signup").count(), 1)
        event = OutboundEvent.objects.get(event_type="newsletter_signup")
        self.assertTrue(event.payload.get("consent_analytics"))

    def test_disallows_external_referer_redirect(self):
        response = self.client.post(
            self.url,
            {"email": "hello@example.com"},
            HTTP_REFERER="https://evil.example/phish",
        )
        self.assertEqual(response.status_code, 302)
        parsed = urlparse(response["Location"])
        self.assertEqual(parsed.path, "/")
