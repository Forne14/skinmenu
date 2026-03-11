from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from catalog.models import Treatment


class AuditContentIntegrityCommandTests(TestCase):
    def test_audit_passes_when_no_issues(self):
        Treatment.objects.create(name="Laser", slug="laser")
        out = StringIO()
        call_command("audit_content_integrity", stdout=out)
        self.assertIn("integrity_issues_total: 0", out.getvalue())
