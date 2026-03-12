from __future__ import annotations

import logging

from .ports import AnalyticsPort, IntegrationEvent

logger = logging.getLogger(__name__)


class ConsentAwareNoopAnalytics(AnalyticsPort):
    def track(self, event: IntegrationEvent) -> None:
        if not event.consented:
            logger.debug("analytics_event_skipped_no_consent name=%s", event.name)
            return
        logger.info("analytics_event_buffered name=%s props=%s", event.name, event.properties)


def track_server_event(*, name: str, properties: dict, consented: bool) -> None:
    adapter = ConsentAwareNoopAnalytics()
    adapter.track(IntegrationEvent(name=name, properties=properties, consented=consented))
