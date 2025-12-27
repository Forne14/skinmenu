from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_setting
class GlobalSiteSettings(BaseSiteSetting):
    clinic_name = models.CharField(max_length=120, default="SKINMENU")
    address = models.TextField(blank=True)
    opening_hours = models.TextField(blank=True, help_text="E.g. Mon–Fri 10:00–19:00")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)

    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("clinic_name"),
                FieldPanel("address"),
                FieldPanel("opening_hours"),
                FieldPanel("phone"),
                FieldPanel("email"),
            ],
            heading="Clinic details",
        ),
        MultiFieldPanel(
            [
                FieldPanel("instagram_url"),
                FieldPanel("tiktok_url"),
                FieldPanel("facebook_url"),
            ],
            heading="Social links",
        ),
    ]
