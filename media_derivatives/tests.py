import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from wagtail.documents import get_document_model

from media_derivatives.models import VideoDerivative
from media_derivatives.worker import transcode_document_video


User = get_user_model()
Document = get_document_model()


class DerivativesStatusViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.doc = Document.objects.create(
            title="source-doc",
            file=SimpleUploadedFile("source.txt", b"hello world", content_type="text/plain"),
        )
        self.derivative = VideoDerivative.objects.create(
            document=self.doc,
            profile_slug="hero_mobile_v1",
            kind=VideoDerivative.Kind.MP4,
            status=VideoDerivative.Status.PROCESSING,
            progress=42,
            error="",
        )
        self.url = reverse("media_derivatives_status", args=[self.doc.id])

    def test_requires_staff_auth(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_returns_derivative_payload_for_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["document_id"], self.doc.id)
        self.assertEqual(len(payload["derivatives"]), 1)
        first = payload["derivatives"][0]
        self.assertEqual(first["kind"], VideoDerivative.Kind.MP4)
        self.assertEqual(first["status"], VideoDerivative.Status.PROCESSING)
        self.assertEqual(first["progress"], 42)
        self.assertEqual(first["rq_job_id"], "")


class WorkerBehaviorTests(TestCase):
    def setUp(self):
        self.doc = Document.objects.create(
            title="worker-doc",
            file=SimpleUploadedFile("worker.txt", b"worker input", content_type="text/plain"),
        )
        self.mp4 = VideoDerivative.objects.create(
            document=self.doc,
            profile_slug="hero_mobile_v1",
            kind=VideoDerivative.Kind.MP4,
            status=VideoDerivative.Status.PENDING,
        )
        self.webm = VideoDerivative.objects.create(
            document=self.doc,
            profile_slug="hero_mobile_v1",
            kind=VideoDerivative.Kind.WEBM,
            status=VideoDerivative.Status.PENDING,
        )

    def test_returns_early_when_already_processing(self):
        self.mp4.status = VideoDerivative.Status.PROCESSING
        self.webm.status = VideoDerivative.Status.PROCESSING
        self.mp4.save(update_fields=["status"])
        self.webm.save(update_fields=["status"])

        with patch("media_derivatives.worker._probe_duration_seconds", side_effect=AssertionError("should not run")):
            transcode_document_video(self.doc.id)

    def test_raises_when_input_path_is_outside_media_root(self):
        realpath = os.path.realpath
        outside = "/tmp/outside-worker-file.txt"

        def fake_realpath(path):
            if path == self.doc.file.path:
                return outside
            return realpath(path)

        with patch("media_derivatives.worker.os.path.realpath", side_effect=fake_realpath):
            with self.assertRaises(ValueError):
                transcode_document_video(self.doc.id)
