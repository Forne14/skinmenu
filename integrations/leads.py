from __future__ import annotations

import hashlib
import logging
from typing import Any
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import OutboundEvent
from .ports import LeadSyncPort

logger = logging.getLogger(__name__)


class NoopLeadSyncAdapter(LeadSyncPort):
    def send(self, payload: dict[str, Any]) -> None:
        logger.info("lead_sync_noop payload=%s", payload)


class WebhookLeadSyncAdapter(LeadSyncPort):
    def __init__(self, webhook_url: str, timeout_seconds: int = 8):
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send(self, payload: dict[str, Any]) -> None:
        if not self.webhook_url:
            raise RuntimeError("LEAD_SYNC_WEBHOOK_URL is not configured")
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=self.timeout_seconds,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()


def _lead_sync_adapter() -> LeadSyncPort:
    backend = getattr(settings, "LEAD_SYNC_BACKEND", "noop").strip().lower()
    if backend == "webhook":
        return WebhookLeadSyncAdapter(
            webhook_url=getattr(settings, "LEAD_SYNC_WEBHOOK_URL", "").strip(),
            timeout_seconds=int(getattr(settings, "LEAD_SYNC_TIMEOUT_SECONDS", 8)),
        )
    return NoopLeadSyncAdapter()


def _retry_delays() -> list[int]:
    raw = str(getattr(settings, "LEAD_SYNC_RETRY_DELAYS", "30,120,300"))
    delays: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if value > 0:
            delays.append(value)
    return delays or [30, 120, 300]


def _max_attempts() -> int:
    return max(1, int(getattr(settings, "LEAD_SYNC_MAX_ATTEMPTS", 3)))


def _schedule_retry(event_id: int, attempt_number: int) -> None:
    if not getattr(settings, "LEAD_SYNC_ENABLED", False):
        return
    try:
        import django_rq
    except Exception:  # noqa: BLE001
        return
    delays = _retry_delays()
    delay_index = min(max(attempt_number - 1, 0), len(delays) - 1)
    delay_seconds = delays[delay_index]
    queue_name = getattr(settings, "LEAD_SYNC_QUEUE", "default")
    q = django_rq.get_queue(queue_name)
    q.enqueue_in(timedelta(seconds=delay_seconds), process_outbound_event, event_id, job_timeout=60)


def _build_newsletter_idempotency_key(payload: dict[str, Any]) -> str:
    email = str(payload.get("email", "")).strip().lower()
    source_url = str(payload.get("source_url", "")).strip()
    date = timezone.now().date().isoformat()
    base = f"newsletter_signup|{email}|{source_url}|{date}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def process_outbound_event(event_id: int) -> None:
    event = OutboundEvent.objects.get(pk=event_id)
    if event.status in {OutboundEvent.STATUS_SENT, OutboundEvent.STATUS_DEAD_LETTER}:
        return
    adapter = _lead_sync_adapter()
    try:
        adapter.send(event.payload)
    except Exception as exc:  # noqa: BLE001
        max_attempts = _max_attempts()
        next_attempt = event.attempts + 1
        if next_attempt >= max_attempts:
            event.mark_dead_letter(str(exc))
            logger.exception("lead_sync_dead_letter event_id=%s", event_id)
            return
        event.mark_failed(str(exc))
        _schedule_retry(event_id=event_id, attempt_number=next_attempt)
        logger.exception("lead_sync_failed event_id=%s", event_id)
    else:
        event.mark_sent()


def enqueue_newsletter_signup(payload: dict[str, Any]) -> OutboundEvent:
    idempotency_key = _build_newsletter_idempotency_key(payload)
    event = (
        OutboundEvent.objects.filter(
            event_type=OutboundEvent.EVENT_NEWSLETTER_SIGNUP,
            idempotency_key=idempotency_key,
        )
        .order_by("-created_at")
        .first()
    )
    if event is None:
        event = OutboundEvent.objects.create(
            event_type=OutboundEvent.EVENT_NEWSLETTER_SIGNUP,
            idempotency_key=idempotency_key,
            destination=getattr(settings, "LEAD_SYNC_BACKEND", "noop"),
            payload=payload,
        )
    if event.status == OutboundEvent.STATUS_SENT:
        return event

    if not getattr(settings, "LEAD_SYNC_ENABLED", False):
        return event

    # Prefer queued dispatch through RQ; fallback to immediate dispatch.
    try:
        import django_rq
    except Exception:  # noqa: BLE001
        process_outbound_event(event.id)
        return event

    queue_name = getattr(settings, "LEAD_SYNC_QUEUE", "default")
    q = django_rq.get_queue(queue_name)
    q.enqueue(process_outbound_event, event.id, job_timeout=60)
    return event
