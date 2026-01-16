# /media_derivatives/templatetags/media_derivatives_tags.py
from __future__ import annotations

from django import template
from django.core.cache import cache

from media_derivatives.models import VideoDerivative

register = template.Library()


def _hero_sources_cache_key(document_id: int, profile_slug: str) -> str:
    return f"hero_video_sources:v1:doc:{document_id}:profile:{profile_slug}"


@register.simple_tag
def hero_video_sources(document_id: int, profile_slug: str = "hero_mobile_v1"):
    """
    Returns a dict of best available sources for a given document.
    Cached in Redis to avoid DB hits on every render.

    Usage:
      {% hero_video_sources doc.id as sources %}
      sources.webm, sources.mp4, sources.poster
    """
    key = _hero_sources_cache_key(int(document_id), str(profile_slug))

    cached = cache.get(key)
    if cached is not None:
        return cached

    qs = (
        VideoDerivative.objects.filter(
            document_id=document_id,
            profile_slug=profile_slug,
            status=VideoDerivative.Status.READY,
        )
        .select_related("poster_image")
    )

    webm = qs.filter(kind=VideoDerivative.Kind.WEBM).first()
    mp4 = qs.filter(kind=VideoDerivative.Kind.MP4).first()

    poster_url = ""
    poster = (webm and webm.poster_image) or (mp4 and mp4.poster_image)
    if poster and getattr(poster, "file", None):
        poster_url = poster.file.url

    data = {
        "webm": webm.file.url if webm and webm.file else "",
        "mp4": mp4.file.url if mp4 and mp4.file else "",
        "poster": poster_url or "",
    }

    # TTL: keep it modest; invalidation in the worker makes it “instant” anyway.
    cache.set(key, data, timeout=60 * 10)  # 10 minutes
    return data
