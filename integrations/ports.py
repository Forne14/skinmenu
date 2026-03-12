from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class IntegrationEvent:
    name: str
    user_id: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    consented: bool = False


class AnalyticsPort(Protocol):
    def track(self, event: IntegrationEvent) -> None: ...


class LeadSyncPort(Protocol):
    def send(self, payload: dict[str, Any]) -> None: ...


class BookingPort(Protocol):
    def build_booking_url(self, *, treatment_slug: str | None = None, option_slug: str | None = None) -> str: ...

