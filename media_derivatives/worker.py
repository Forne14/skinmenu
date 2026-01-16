# /media_derivatives/worker.py
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from typing import Callable, Optional

from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.models import Collection

from .models import VideoDerivative

Document = get_document_model()
Image = get_image_model()

_PROGRESS_RE = re.compile(r"^out_time_ms=(\d+)$")


def _hero_sources_cache_key(document_id: int, profile_slug: str) -> str:
    return f"hero_video_sources:v1:doc:{document_id}:profile:{profile_slug}"


def _safe_stem_from_doc(doc) -> str:
    """
    Use the original filename (without extension) as a stable stem.
    Example: documents/foo/bar/my_video.mp4 -> my_video
    """
    name = getattr(doc.file, "name", "") or ""
    base = os.path.basename(name)
    stem, _ext = os.path.splitext(base)
    stem = stem.strip() or f"doc_{doc.id}"
    # basic sanitize: keep letters/numbers/_/-
    stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", stem)
    return stem[:120]


def _probe_duration_seconds(input_path: str) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_path,
        ],
        text=True,
    ).strip()
    return float(out) if out else 0.0


def _run_with_progress(
    cmd: list[str],
    *,
    timeout_seconds: int,
    on_out_time_ms: Callable[[int], None] | None = None,
) -> None:
    """
    Run ffmpeg while streaming stdout so we don't buffer huge output in memory.
    Parse `-progress pipe:1` lines like `out_time_ms=...` to update progress.
    Enforce a hard timeout.
    """
    start = time.time()
    print("RUNNING:", " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # combine streams; keeps order
        text=True,
        bufsize=1,  # line-buffered
        universal_newlines=True,
    )

    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            # Optional: keep logs lighter
            # print(line)

            m = _PROGRESS_RE.match(line)
            if m and on_out_time_ms is not None:
                on_out_time_ms(int(m.group(1)))

            if time.time() - start > timeout_seconds:
                proc.kill()
                proc.wait()
                raise RuntimeError(f"ffmpeg timed out after {timeout_seconds}s: {' '.join(cmd)}")

        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"Command failed (exit {rc}): {' '.join(cmd)}")

    finally:
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass


def transcode_document_video(document_id: int, profile_slug: str = "hero_mobile_v1") -> None:
    """
    RQ job entrypoint.

    Output strategy:
      1) Poster first (fast)  -> editors see *something* ASAP
      2) MP4 (H.264) next     -> broad support
      3) WebM last (VP9)      -> best-effort

    Files are saved to VideoDerivative.file (upload_to controls final path).
    """
    doc = Document.objects.get(id=document_id)

    webm = VideoDerivative.objects.get(
        document=doc, profile_slug=profile_slug, kind=VideoDerivative.Kind.WEBM
    )
    mp4 = VideoDerivative.objects.get(
        document=doc, profile_slug=profile_slug, kind=VideoDerivative.Kind.MP4
    )

    input_path = doc.file.path  # assumes local filesystem storage
    stem = _safe_stem_from_doc(doc)

    # duration for progress
    duration_s = _probe_duration_seconds(input_path)
    duration_ms = max(1, int(duration_s * 1000))

    now = timezone.now()
    with transaction.atomic():
        for d in (webm, mp4):
            d.status = VideoDerivative.Status.PROCESSING
            d.progress = 0
            d.started_at = now
            d.finished_at = None
            d.error = ""
            d.save(update_fields=["status", "progress", "started_at", "finished_at", "error", "updated_at"])

    poster_img = None

    def _fail_all(msg: str) -> None:
        """
        Ensure we never leave rows in PROCESSING.
        """
        ts = timezone.now()
        VideoDerivative.objects.filter(pk__in=[mp4.pk, webm.pk]).update(
            status=VideoDerivative.Status.FAILED,
            error=msg,
            finished_at=ts,
            progress=0,
            updated_at=ts,
        )
        cache.delete(_hero_sources_cache_key(document_id, profile_slug))

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            poster_out = os.path.join(tmpdir, "poster.jpg")
            mp4_out = os.path.join(tmpdir, "out.mp4")
            webm_out = os.path.join(tmpdir, "out.webm")

            # -----------------------
            # 1) Poster (JPEG, 1 frame)
            # -----------------------
            # JPEG works reliably with Wagtail metadata extraction.
            _run_with_progress(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-ss",
                    "0.25",
                    "-i",
                    input_path,
                    "-vframes",
                    "1",
                    "-q:v",
                    "3",
                    poster_out,
                ],
                timeout_seconds=30,
                on_out_time_ms=None,
            )

            if not os.path.exists(poster_out) or os.path.getsize(poster_out) == 0:
                raise RuntimeError("Poster output was not created or is empty.")

            root_collection = Collection.get_first_root_node()
            with open(poster_out, "rb") as f:
                poster_img = Image(
                    title=f"Poster: {doc.title}",
                    collection=root_collection,
                    file=File(f, name=f"{stem}__{profile_slug}__poster.jpg"),
                )
                poster_img.save()

            # -----------------------
            # 2) MP4 (H.264)
            # -----------------------
            def mp4_progress(out_time_ms: int) -> None:
                pct = min(99, int(out_time_ms / duration_ms * 100))
                VideoDerivative.objects.filter(pk=mp4.pk).update(progress=pct)

            _run_with_progress(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-nostats",
                    "-progress",
                    "pipe:1",
                    "-i",
                    input_path,
                    "-vf",
                    "scale=720:-2,fps=30",
                    "-c:v",
                    "libx264",
                    "-profile:v",
                    "main",
                    "-preset",
                    "veryfast",
                    "-b:v",
                    "1800k",
                    "-maxrate",
                    "2200k",
                    "-bufsize",
                    "4400k",
                    "-g",
                    "60",
                    "-movflags",
                    "+faststart",
                    "-an",
                    mp4_out,
                ],
                timeout_seconds=180,
                on_out_time_ms=mp4_progress,
            )

            if not os.path.exists(mp4_out) or os.path.getsize(mp4_out) == 0:
                raise RuntimeError("MP4 output file was not created or is empty.")

            with transaction.atomic():
                with open(mp4_out, "rb") as f:
                    # Use a deterministic name to avoid confusing overwrites
                    mp4.file.save(
                        f"{stem}__{profile_slug}.mp4",
                        ContentFile(f.read()),
                        save=False,
                    )
                mp4.poster_image = poster_img
                mp4.status = VideoDerivative.Status.READY
                mp4.progress = 100
                mp4.finished_at = timezone.now()
                mp4.error = ""
                mp4.save()
            cache.delete(_hero_sources_cache_key(document_id, profile_slug))

            # -----------------------
            # 3) WebM (VP9) best-effort
            # -----------------------
            def webm_progress(out_time_ms: int) -> None:
                pct = min(99, int(out_time_ms / duration_ms * 100))
                VideoDerivative.objects.filter(pk=webm.pk).update(progress=pct)

            try:
                _run_with_progress(
                    [
                        "ffmpeg",
                        "-y",
                        "-hide_banner",
                        "-nostats",
                        "-progress",
                        "pipe:1",
                        "-i",
                        input_path,
                        "-vf",
                        "scale=720:-2,fps=30",
                        "-c:v",
                        "libvpx-vp9",
                        "-deadline",
                        "realtime",
                        "-cpu-used",
                        "6",
                        "-b:v",
                        "1200k",
                        "-maxrate",
                        "1500k",
                        "-bufsize",
                        "3000k",
                        "-row-mt",
                        "1",
                        "-threads",
                        "4",
                        "-g",
                        "60",
                        "-an",
                        webm_out,
                    ],
                    timeout_seconds=240,
                    on_out_time_ms=webm_progress,
                )

                if not os.path.exists(webm_out) or os.path.getsize(webm_out) == 0:
                    raise RuntimeError("WebM output file was not created or is empty.")

                with transaction.atomic():
                    with open(webm_out, "rb") as f:
                        webm.file.save(
                            f"{stem}__{profile_slug}.webm",
                            ContentFile(f.read()),
                            save=False,
                        )
                    webm.poster_image = poster_img
                    webm.status = VideoDerivative.Status.READY
                    webm.progress = 100
                    webm.finished_at = timezone.now()
                    webm.error = ""
                    webm.save()

            except Exception as e:
                # WebM optional: mark only WebM as failed
                webm.status = VideoDerivative.Status.FAILED
                webm.error = f"WebM failed: {e}"
                webm.finished_at = timezone.now()
                webm.save(update_fields=["status", "error", "finished_at", "updated_at"])
            finally:
                cache.delete(_hero_sources_cache_key(document_id, profile_slug))

    except Exception as e:
        _fail_all(f"Transcode failed: {e}")
        raise
