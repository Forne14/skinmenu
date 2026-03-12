from __future__ import annotations

from django.conf import settings
from urllib.parse import urlencode

from .ports import BookingPort


class QueryStringBookingAdapter(BookingPort):
    def build_booking_url(self, *, treatment_slug: str | None = None, option_slug: str | None = None) -> str:
        base_url = getattr(settings, "BOOKING_BASE_URL", "").strip()
        if not base_url:
            return ""
        params: dict[str, str] = {}
        if treatment_slug:
            params["treatment"] = treatment_slug
        if option_slug:
            params["option"] = option_slug
        if not params:
            return base_url
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode(params)}"

