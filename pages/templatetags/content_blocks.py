from __future__ import annotations

from typing import Iterable

from django import template

from catalog.models import ContentBlock

register = template.Library()

def _unwrap_block(block):
    return getattr(block, "block", block)


@register.inclusion_tag("pages/blocks/content_block.html", takes_context=True)
def render_content_block(context, block: ContentBlock):
    return {
        "request": context.get("request"),
        "block": _unwrap_block(block),
    }


@register.inclusion_tag("pages/blocks/content_block_list.html", takes_context=True)
def render_content_blocks(context, blocks: Iterable[ContentBlock]):
    queryset = blocks
    if hasattr(queryset, "select_related") and hasattr(queryset, "model"):
        model_fields = {f.name for f in queryset.model._meta.get_fields()}
        if "block" in model_fields:
            queryset = queryset.select_related("block")
    return {
        "request": context.get("request"),
        "blocks": [_unwrap_block(b) for b in queryset],
    }
