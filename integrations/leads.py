from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

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


def process_outbound_event(event_id: int) -> None:
    event = OutboundEvent.objects.get(pk=event_id)
    adapter = _lead_sync_adapter()
    try:
        adapter.send(event.payload)
    except Exception as exc:  # noqa: BLE001
        event.mark_failed(str(exc))
        logger.exception("lead_sync_failed event_id=%s", event_id)
        raise
    else:
        event.mark_sent()


def enqueue_newsletter_signup(payload: dict[str, Any]) -> OutboundEvent:
    event = OutboundEvent.objects.create(
        event_type=OutboundEvent.EVENT_NEWSLETTER_SIGNUP,
        destination=getattr(settings, "LEAD_SYNC_BACKEND", "noop"),
        payload=payload,
    )

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

