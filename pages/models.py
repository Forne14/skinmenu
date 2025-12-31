from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

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
