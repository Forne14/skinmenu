# /media_derivatives/signals.py
from __future__ import annotations

import os

import django_rq
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from wagtail.documents import get_document_model

from .models import VideoDerivative
from .worker import transcode_document_video

Document = get_document_model()

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv", ".wmv", ".mpg", ".mpeg"}


def _is_video_document(doc) -> bool:
    name = getattr(doc.file, "name", "") or ""
    _, ext = os.path.splitext(name.lower())
    return ext in VIDEO_EXTS


@receiver(post_save, sender=Document)
def on_document_saved(sender, instance, created: bool, **kwargs):
    """
    When a new video Document is uploaded:
    - ensure derivative rows exist (mp4 + webm)
    - enqueue an RQ job AFTER the DB transaction commits (prevents weird states)
    """
    if not instance.file:
        return

    # Enqueue only on create. (We can add "file changed" detection later.)
    if not created:
        return

    if not _is_video_document(instance):
        return

    profile = "hero_mobile_v1"

    VideoDerivative.objects.get_or_create(
        document=instance, profile_slug=profile, kind=VideoDerivative.Kind.MP4
    )
    VideoDerivative.objects.get_or_create(
        document=instance, profile_slug=profile, kind=VideoDerivative.Kind.WEBM
    )

    def _enqueue():
        q = django_rq.get_queue("default")
        job = q.enqueue(
            transcode_document_video,
            instance.id,
            profile,
            job_timeout=60 * 30,  # 10 min safety
            result_ttl=0,
        )
        VideoDerivative.objects.filter(document=instance, profile_slug=profile).update(rq_job_id=job.id)

    transaction.on_commit(_enqueue)
