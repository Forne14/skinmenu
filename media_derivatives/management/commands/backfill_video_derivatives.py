from __future__ import annotations

import os

import django_rq
from django.core.management.base import BaseCommand
from wagtail.documents import get_document_model

from media_derivatives.models import VideoDerivative
from media_derivatives.worker import transcode_document_video


VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv", ".wmv", ".mpg", ".mpeg"}


class Command(BaseCommand):
    help = "Backfill video derivatives for existing Wagtail Document uploads."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            default="hero_mobile_v1",
            help="Derivative profile slug to backfill (default: hero_mobile_v1).",
        )
        parser.add_argument(
            "--queue",
            default="default",
            help="RQ queue name (default: default).",
        )
        parser.add_argument(
            "--doc-ids",
            default="",
            help="Optional comma-separated list of Document IDs to process.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be queued without enqueuing jobs.",
        )

    def handle(self, *args, **options):
        profile = options["profile"]
        queue_name = options["queue"]
        dry_run = options["dry_run"]
        doc_ids_raw = options["doc_ids"].strip()

        doc_ids = []
        if doc_ids_raw:
            for token in doc_ids_raw.split(","):
                token = token.strip()
                if token:
                    doc_ids.append(int(token))

        Document = get_document_model()
        docs = Document.objects.exclude(file="")
        if doc_ids:
            docs = docs.filter(id__in=doc_ids)

        q = django_rq.get_queue(queue_name)

        scanned = 0
        queued = 0
        skipped = 0

        for doc in docs.iterator():
            scanned += 1
            name = getattr(doc.file, "name", "") or ""
            _base, ext = os.path.splitext(name.lower())
            if ext not in VIDEO_EXTS:
                continue

            existing = VideoDerivative.objects.filter(document=doc, profile_slug=profile)
            existing_by_kind = {d.kind: d for d in existing}

            created_any = False
            for kind in (VideoDerivative.Kind.MP4, VideoDerivative.Kind.WEBM):
                if kind not in existing_by_kind:
                    VideoDerivative.objects.create(
                        document=doc,
                        profile_slug=profile,
                        kind=kind,
                        status=VideoDerivative.Status.PENDING,
                    )
                    created_any = True

            existing = VideoDerivative.objects.filter(document=doc, profile_slug=profile)
            needs_work = existing.filter(
                status__in=[
                    VideoDerivative.Status.PENDING,
                    VideoDerivative.Status.FAILED,
                ]
            ).exists()

            if not created_any and not needs_work:
                skipped += 1
                continue

            if dry_run:
                queued += 1
                self.stdout.write(f"[dry-run] enqueue doc={doc.id} profile={profile}")
                continue

            job = q.enqueue(
                transcode_document_video,
                doc.id,
                profile,
                job_timeout=60 * 30,
                result_ttl=0,
            )
            VideoDerivative.objects.filter(document=doc, profile_slug=profile).update(
                rq_job_id=job.id
            )
            queued += 1
            self.stdout.write(f"queued doc={doc.id} job={job.id} profile={profile}")

        self.stdout.write(
            f"done scanned={scanned} queued={queued} skipped={skipped} dry_run={dry_run}"
        )
