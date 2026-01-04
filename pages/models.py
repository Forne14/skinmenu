from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail import blocks

from .blocks import HomeSections


class HomePage(Page):
    sections = StreamField(
        HomeSections(),
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("sections"),
    ]

    max_count = 1

    class Meta:
        verbose_name = "Homepage"


class StandardPage(Page):
    """
    Generic content page (About, Contact, Policies, etc.)
    Keep it simple for now: rich text + headings via StreamField.
    """

    body = StreamField(
        [
            ("heading", blocks.CharBlock(required=True, max_length=120)),
            ("text", blocks.RichTextBlock(features=["bold", "italic", "link", "ol", "ul"])),
        ],
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "Standard page"
