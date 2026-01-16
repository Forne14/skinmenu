# /media_derivatives/models.py
from __future__ import annotations

import os
from django.db import models
from django.utils import timezone
from wagtail.documents import get_document_model
from wagtail.images import get_image_model


Document = get_document_model()
Image = get_image_model()


def _derived_upload_path(instance: "VideoDerivative", filename: str) -> str:
    """
    Store derivatives under a stable namespace so we can:
    - set long-lived cache headers later for /media/derived/
    - keep originals untouched under /media/documents/
    """
    # Example:
    # derived/videos/123/hero_mobile_v1/video.webm
    doc_id = instance.document_id or "unknown"
    profile = instance.profile_slug or "default"
    base, ext = os.path.splitext(filename)
    ext = ext.lower().lstrip(".") or "bin"

    # Keep filenames predictable
    if instance.kind == VideoDerivative.Kind.WEBM:
        out_name = f"video.webm"
    elif instance.kind == VideoDerivative.Kind.MP4:
        out_name = f"video.mp4"
    else:
        out_name = f"file.{ext}"

    return f"derived/videos/{doc_id}/{profile}/{out_name}"


class VideoDerivative(models.Model):
    """
    Tracks transcoded / generated assets derived from an uploaded Wagtail Document.

    We intentionally keep the original Document file untouched and store:
      - a WebM derivative (primary)
      - an MP4 derivative (fallback)
      - a poster image (optional)
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class Kind(models.TextChoices):
        WEBM = "webm", "WebM"
        MP4 = "mp4", "MP4"
        OTHER = "other", "Other"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="video_derivatives",
        help_text="The original uploaded Wagtail Document this derivative was produced from.",
    )

    # Allows you to evolve outputs safely over time:
    # e.g. hero_mobile_v1 -> hero_mobile_v2 without breaking caching or templates.
    profile_slug = models.SlugField(
        max_length=64,
        default="hero_mobile_v1",
        help_text="Derivative profile identifier (e.g. hero_mobile_v1).",
    )

    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        default=Kind.WEBM,
        help_text="What type of derivative this row represents.",
    )

    file = models.FileField(
        upload_to=_derived_upload_path,
        blank=True,
        null=True,
        help_text="The generated derivative file (e.g. .webm or .mp4).",
    )

    poster_image = models.ForeignKey(
        Image,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        help_text="Optional poster image generated from the video (stored as a Wagtail Image).",
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    progress = models.PositiveSmallIntegerField(
        default=0,
        help_text="0-100 progress for this derivative generation.",
    )

    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    rq_job_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="RQ job id for the job currently/last producing this derivative.",
    )


    # Used to prevent unnecessary re-processing and enable safe backfill
    source_etag = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Optional: etag or content fingerprint of the source Document file at time of processing.",
    )

    error = models.TextField(
        blank=True,
        default="",
        help_text="If processing failed, store a human-readable error message here.",
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "profile_slug", "kind"],
                name="uniq_video_derivative_per_doc_profile_kind",
            )
        ]
        indexes = [
            models.Index(fields=["document", "profile_slug"]),
            models.Index(fields=["document", "profile_slug", "kind"], name="idx_derivative_lookup"),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_id} {self.profile_slug} {self.kind} ({self.status})"
