# /media_derivatives/worker.py
from __future__ import annotations

import os
import re
import select
import subprocess
import tempfile
import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.models import Collection

from .models import VideoDerivative


class AlreadyProcessingError(Exception):
    """Raised when another worker is already processing this document."""
    pass

Document = get_document_model()
Image = get_image_model()

_PROGRESS_RE = re.compile(r"^out_time_ms=(\d+)$")


def _hero_sources_cache_key(document_id: int, profile_slug: str) -> str:
    return f"hero_video_sources:v1:doc:{document_id}:profile:{profile_slug}"


def _safe_stem_from_doc(doc) -> str:
    name = getattr(doc.file, "name", "") or ""
    base = os.path.basename(name)
    stem, _ext = os.path.splitext(base)
    stem = stem.strip() or f"doc_{doc.id}"
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
    label: str = "ffmpeg",
) -> None:
    """
    Run ffmpeg while:
      - streaming output when available (truly non-blocking)
      - enforcing a hard timeout even if the process produces no output
      - parsing -progress pipe:1 lines (out_time_ms=...) when present

    Uses os.set_blocking(False) + os.read() to avoid readline() blocking issues.
    """
    from collections import deque

    start = time.time()
    last_heartbeat = start
    last_data_time = start
    tail = deque(maxlen=200)
    buffer = b""

    print(f"RUNNING({label}):", " ".join(cmd), flush=True)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert proc.stdout is not None
    fd = proc.stdout.fileno()

    # Make stdout non-blocking
    os.set_blocking(fd, False)

    def _kill_and_raise(msg: str) -> None:
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass

        debug_tail = "\n".join(list(tail)[-50:])
        raise RuntimeError(
            f"{msg}\n\nCommand:\n  {' '.join(cmd)}\n\nLast output (tail):\n{debug_tail}\n"
        )

    def _process_buffer() -> None:
        nonlocal buffer, last_data_time
        # Split buffer into lines
        while b"\n" in buffer:
            line_bytes, buffer = buffer.split(b"\n", 1)
            try:
                line = line_bytes.decode("utf-8", errors="replace").strip()
            except Exception:
                continue
            if not line:
                continue

            tail.append(line)
            last_data_time = time.time()

            m = _PROGRESS_RE.match(line)
            if m and on_out_time_ms is not None:
                on_out_time_ms(int(m.group(1)))

    try:
        while True:
            now = time.time()

            # Timeout enforcement even when ffmpeg is silent
            if now - start > timeout_seconds:
                _kill_and_raise(f"{label} timed out after {timeout_seconds}s")

            # Heartbeat every 5 seconds
            if now - last_heartbeat > 5:
                elapsed = int(now - start)
                silent_for = int(now - last_data_time)
                print(f"[{label}] alive: elapsed={elapsed}s, silent_for={silent_for}s", flush=True)
                last_heartbeat = now

            # Try to read available data (non-blocking)
            try:
                chunk = os.read(fd, 4096)
                if chunk:
                    buffer += chunk
                    _process_buffer()
            except BlockingIOError:
                # No data available right now, that's fine
                pass
            except OSError:
                # Pipe closed or error
                pass

            # Check if process exited
            rc = proc.poll()
            if rc is not None:
                # Drain any remaining data
                try:
                    while True:
                        chunk = os.read(fd, 4096)
                        if not chunk:
                            break
                        buffer += chunk
                except (BlockingIOError, OSError):
                    pass

                # Process remaining buffer (including incomplete last line)
                _process_buffer()
                if buffer.strip():
                    try:
                        tail.append(buffer.decode("utf-8", errors="replace").strip())
                    except Exception:
                        pass

                if rc != 0:
                    _kill_and_raise(f"{label} failed (exit {rc})")

                print(f"[{label}] completed in {int(now - start)}s", flush=True)
                return

            # Brief sleep to avoid busy-waiting
            time.sleep(0.1)

    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass


def transcode_document_video(document_id: int, profile_slug: str = "hero_mobile_v1") -> None:
    doc = Document.objects.get(id=document_id)

    # -------------------------------------------------------------------------
    # RACE CONDITION FIX: Use atomic conditional update to claim the job.
    # Only proceed if we successfully transition from PENDING → PROCESSING.
    # This works on SQLite (unlike select_for_update which requires PostgreSQL).
    # -------------------------------------------------------------------------
    now = timezone.now()

    # Atomically claim both derivatives by updating only PENDING rows
    claimed_count = VideoDerivative.objects.filter(
        document=doc,
        profile_slug=profile_slug,
        kind__in=[VideoDerivative.Kind.MP4, VideoDerivative.Kind.WEBM],
        status__in=[VideoDerivative.Status.PENDING, VideoDerivative.Status.FAILED],
    ).update(
        status=VideoDerivative.Status.PROCESSING,
        progress=0,
        started_at=now,
        finished_at=None,
        error="",
        updated_at=now,
    )

    if claimed_count == 0:
        # Either already processing/ready, or rows don't exist
        # Check if already complete
        mp4_ready = VideoDerivative.objects.filter(
            document=doc,
            profile_slug=profile_slug,
            kind=VideoDerivative.Kind.MP4,
            status=VideoDerivative.Status.READY,
        ).exists()

        if mp4_ready:
            print(f"[transcode] document_id={document_id} already has MP4 ready, skipping", flush=True)
        else:
            print(f"[transcode] document_id={document_id} is being processed by another worker, skipping", flush=True)
        return

    # Fetch the derivatives we just claimed
    mp4 = VideoDerivative.objects.filter(
        document=doc, profile_slug=profile_slug, kind=VideoDerivative.Kind.MP4
    ).first()
    webm = VideoDerivative.objects.filter(
        document=doc, profile_slug=profile_slug, kind=VideoDerivative.Kind.WEBM
    ).first()

    if not mp4 or not webm:
        raise ValueError(f"Missing derivative rows for document_id={document_id}")

    # -------------------------------------------------------------------------
    # PATH TRAVERSAL FIX: Validate file is within MEDIA_ROOT
    # -------------------------------------------------------------------------
    input_path = doc.file.path
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    real_input_path = os.path.realpath(input_path)

    if not real_input_path.startswith(media_root + os.sep):
        raise ValueError(f"File path '{input_path}' is outside MEDIA_ROOT")

    if not os.path.isfile(real_input_path):
        raise FileNotFoundError(f"Source file does not exist: {real_input_path}")

    stem = _safe_stem_from_doc(doc)

    duration_s = _probe_duration_seconds(input_path)
    duration_ms = max(1, int(duration_s * 1000))

    def _fail_all(msg: str) -> None:
        ts = timezone.now()
        VideoDerivative.objects.filter(pk__in=[mp4.pk, webm.pk]).update(
            status=VideoDerivative.Status.FAILED,
            error=msg,
            finished_at=ts,
            progress=0,
            updated_at=ts,
        )
        cache.delete(_hero_sources_cache_key(document_id, profile_slug))

    poster_img = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            poster_out = os.path.join(tmpdir, "poster.jpg")
            mp4_out = os.path.join(tmpdir, "out.mp4")
            webm_out = os.path.join(tmpdir, "out.webm")

            # -----------------------
            # 1) Poster
            # -----------------------
            # Give immediate "life sign" progress
            VideoDerivative.objects.filter(pk__in=[mp4.pk, webm.pk]).update(progress=1)

            # poster can sometimes emit no progress lines; timeout must still work
            _run_with_progress(
                [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "warning",
                    # reduce probe overhead
                    "-probesize",
                    "32k",
                    "-analyzeduration",
                    "0",
                    # fast seek
                    "-ss",
                    "0.25",
                    "-i",
                    input_path,
                    "-frames:v",
                    "1",
                    "-update",
                    "1",
                    "-q:v",
                    "3",
                    poster_out,
                ],
                label="poster",
                timeout_seconds=30,
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

            # CRITICAL: attach poster_image NOW so /status/ shows poster_url immediately
            VideoDerivative.objects.filter(pk__in=[mp4.pk, webm.pk]).update(
                poster_image_id=poster_img.id,
                progress=5,
            )

            # -----------------------
            # 2) MP4 (required)
            # -----------------------
            def mp4_progress(out_time_ms: int) -> None:
                pct = min(99, int(out_time_ms / duration_ms * 100))
                VideoDerivative.objects.filter(pk=mp4.pk).update(progress=max(5, pct))

            _run_with_progress(
                [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "warning",
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
                label="mp4",
            )

            if not os.path.exists(mp4_out) or os.path.getsize(mp4_out) == 0:
                raise RuntimeError("MP4 output file was not created or is empty.")

            with transaction.atomic():
                with open(mp4_out, "rb") as f:
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
            # 3) WebM (optional best-effort)
            # -----------------------
            # DESIGN NOTE: WebM is independent of MP4. If WebM fails, MP4 remains
            # READY and usable. This is intentional - MP4 has universal browser
            # support while WebM is a nice-to-have optimization.

            def webm_progress(out_time_ms: int) -> None:
                pct = min(99, int(out_time_ms / duration_ms * 100))
                VideoDerivative.objects.filter(pk=webm.pk).update(progress=max(5, pct))

            webm_pk = webm.pk  # Capture PK for atomic updates

            try:
                _run_with_progress(
                    [
                        "ffmpeg",
                        "-y",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "warning",
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
                    timeout_seconds=900,
                    on_out_time_ms=webm_progress,
                    label="webm",
                )

                if not os.path.exists(webm_out) or os.path.getsize(webm_out) == 0:
                    raise RuntimeError("WebM output file was not created or is empty.")

                # Refresh webm from DB to avoid stale object issues
                webm = VideoDerivative.objects.get(pk=webm_pk)
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
                # ATOMICITY FIX: Use queryset.update() instead of object.save()
                # to avoid race conditions with stale object data
                error_msg = f"WebM failed: {e}"
                print(f"[webm] {error_msg}", flush=True)
                VideoDerivative.objects.filter(pk=webm_pk).update(
                    status=VideoDerivative.Status.FAILED,
                    error=error_msg[:1000],  # Truncate to avoid DB field overflow
                    finished_at=timezone.now(),
                    updated_at=timezone.now(),
                )
            finally:
                cache.delete(_hero_sources_cache_key(document_id, profile_slug))

    except Exception as e:
        _fail_all(f"Transcode failed: {e}")
        raise
