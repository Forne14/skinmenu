from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _abs(request, url: str) -> str:
    try:
        return request.build_absolute_uri(url)
    except Exception:
        return url


def _page_abs_url(request, page) -> str:
    """
    Works with Wagtail Page-like objects without importing Page.
    """
    try:
        # Wagtail's preferred URL resolver when request is available
        url = page.get_url(request=request)
        return request.build_absolute_uri(url)
    except Exception:
        try:
            return request.build_absolute_uri(page.url)
        except Exception:
            return page.url or "/"


def _image_rendition_abs(request, image, spec: str) -> Optional[str]:
    """
    Uses renditions if possible without importing Image types.
    """
    if not image:
        return None
    try:
        rendition = image.get_rendition(spec)
        return _abs(request, rendition.url)
    except Exception:
        try:
            return _abs(request, image.file.url)
        except Exception:
            return None


def _breadcrumbs(page, request) -> Optional[Dict[str, Any]]:
    # Skip breadcrumb on very shallow pages (home + direct children)
    try:
        if page.depth <= 3:
            return None
    except Exception:
        pass

    try:
        ancestors = page.get_ancestors(inclusive=True).live().public()
    except Exception:
        return None

    items: List[Dict[str, Any]] = []
    pos = 1
    for p in ancestors:
        try:
            if p.is_root():
                continue
        except Exception:
            pass

        url = _page_abs_url(request, p)
        if not url:
            continue

        items.append(
            {
                "@type": "ListItem",
                "position": pos,
                "name": getattr(p, "title", ""),
                "item": url,
            }
        )
        pos += 1

    if len(items) < 2:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


def _organization(site_settings, request) -> Optional[Dict[str, Any]]:
    """
    Reads GlobalSiteSettings from the object you already pass into templates:
      {% get_settings as site_settings %}
      ... include header/footer with settings=site_settings ...
    So site_settings is a proxy that exposes site_settings.site_settings.GlobalSiteSettings
    """
    if not site_settings:
        return None

    try:
        gs = site_settings.site_settings.GlobalSiteSettings
    except Exception:
        return None

    name = getattr(gs, "clinic_name", None) or "SKINMENU"
    url = _abs(request, "/")

    same_as: List[str] = []
    for key in ("instagram_url", "tiktok_url", "facebook_url", "youtube_url", "linkedin_url"):
        v = (getattr(gs, key, "") or "").strip()
        if v:
            same_as.append(v)

    address_text = (getattr(gs, "address", "") or "").strip()
    email = (getattr(gs, "email", "") or "").strip()

    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": ["LocalBusiness", "MedicalClinic"],
        "name": name,
        "url": url,
    }

    if email:
        data["email"] = email

    if same_as:
        data["sameAs"] = same_as

    if address_text:
        # Conservative representation; you can split into locality/postcode later
        data["address"] = {"@type": "PostalAddress", "streetAddress": address_text}

    return data


def _page_specific(page, request) -> List[Dict[str, Any]]:
    """
    Page models can expose:
      def get_structured_data(self, request) -> list[dict]
    """
    specific = getattr(page, "specific", page)
    if hasattr(specific, "get_structured_data"):
        try:
            data = specific.get_structured_data(request)  # type: ignore[attr-defined]
            if not data:
                return []
            return [d for d in data if isinstance(d, dict)]
        except Exception:
            return []
    return []


@register.simple_tag(takes_context=True)
def canonical_url(context) -> str:
    request = context.get("request")
    page = context.get("page")
    if request and page:
        return _page_abs_url(request, page)
    if request:
        try:
            return request.build_absolute_uri("/")
        except Exception:
            return "/"
    return "/"


@register.simple_tag(takes_context=True)
def og_image_url(context) -> str:
    """
    Tries best available page image with a sensible rendition.
    Expects pages to use `featured_image` commonly.
    """
    request = context.get("request")
    page = context.get("page")
    if not request or not page:
        return ""

    specific = getattr(page, "specific", page)
    img = getattr(specific, "featured_image", None) or getattr(specific, "hero_image", None)

    url = _image_rendition_abs(request, img, "fill-1600x900")
    return url or ""


@register.simple_tag(takes_context=True)
def schema_json_ld(context) -> str:
    request = context.get("request")
    page = context.get("page")
    site_settings = context.get("site_settings")

    if not request or not page:
        return ""

    payloads: List[Dict[str, Any]] = []

    org = _organization(site_settings, request)
    if org:
        payloads.append(org)

    crumb = _breadcrumbs(page, request)
    if crumb:
        payloads.append(crumb)

    payloads.extend(_page_specific(page, request))

    if not payloads:
        return ""

    scripts = []
    for obj in payloads:
        scripts.append(
            '<script type="application/ld+json">{}</script>'.format(
                json.dumps(obj, ensure_ascii=False)
            )
        )

    return mark_safe("\n".join(scripts))
