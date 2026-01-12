from __future__ import annotations

import re

from django import template
from django.contrib.staticfiles import finders
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

_FILL_ATTR_RE = re.compile(r'fill="(?!none)[^"]*"', flags=re.IGNORECASE)
_SVG_TAG_RE = re.compile(r"<svg\b([^>]*)>", flags=re.IGNORECASE)
_TITLE_TAG_RE = re.compile(r"<title>.*?</title>", flags=re.IGNORECASE | re.DOTALL)


def _inject_attr(svg_tag_attrs: str, name: str, value: str) -> str:
    attr_re = re.compile(rf'\b{name}="[^"]*"', flags=re.IGNORECASE)
    if attr_re.search(svg_tag_attrs):
        return attr_re.sub(f'{name}="{conditional_escape(value)}"', svg_tag_attrs)
    return f'{svg_tag_attrs} {name}="{conditional_escape(value)}"'


@register.simple_tag
def svg(path: str, css_class: str = "", title: str = "", aria_label: str = ""):
    if not path:
        return ""

    resolved = finders.find(path)
    if not resolved:
        return mark_safe(f"<!-- svg: NOT FOUND {conditional_escape(path)} -->")

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return mark_safe(f"<!-- svg: UNREADABLE {conditional_escape(path)} -->")

    if title:
        raw = _TITLE_TAG_RE.sub("", raw)

    raw = _FILL_ATTR_RE.sub('fill="currentColor"', raw)

    m = _SVG_TAG_RE.search(raw)
    if not m:
        return mark_safe(f"<!-- svg: INVALID SVG (no <svg>) {conditional_escape(path)} -->")

    svg_attrs = (m.group(1) or "").strip()

    # ensure inheritance even if <path> has no fill attr
    if not re.search(r'\bfill="[^"]*"', svg_attrs, flags=re.IGNORECASE):
        svg_attrs = _inject_attr(svg_attrs, "fill", "currentColor")

    if css_class:
        class_re = re.compile(r'\bclass="([^"]*)"', flags=re.IGNORECASE)
        class_match = class_re.search(svg_attrs)
        if class_match:
            existing = class_match.group(1).strip()
            merged = f"{existing} {css_class}".strip()
            svg_attrs = class_re.sub(f'class="{conditional_escape(merged)}"', svg_attrs)
        else:
            svg_attrs = _inject_attr(svg_attrs, "class", css_class)

    label = aria_label or title
    if label:
        svg_attrs = _inject_attr(svg_attrs, "role", "img")
        svg_attrs = _inject_attr(svg_attrs, "aria-label", label)
        svg_attrs = re.sub(r'\baria-hidden="[^"]*"', "", svg_attrs, flags=re.IGNORECASE).strip()
    else:
        svg_attrs = _inject_attr(svg_attrs, "aria-hidden", "true")

    raw = _SVG_TAG_RE.sub(f"<svg {svg_attrs}>", raw, count=1)

    if title:
        raw = re.sub(
            r"(<svg[^>]*>)",
            r"\1" + f"<title>{conditional_escape(title)}</title>",
            raw,
            count=1,
            flags=re.IGNORECASE,
        )

    return mark_safe(raw)
