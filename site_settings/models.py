from django.db import models

from colorfield.fields import ColorField
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

    # Newsletter (simple, editor-friendly)
    newsletter_heading = models.CharField(max_length=80, default="Stay in the know", blank=True)
    newsletter_copy = models.CharField(max_length=180, default="Enter your email to stay in the know", blank=True)
    newsletter_form_action = models.URLField(
        blank=True,
        help_text="Optional: external newsletter form endpoint (Mailchimp/ConvertKit). Leave blank to hide the form.",
    )
    newsletter_button_label = models.CharField(max_length=40, default="Subscribe", blank=True)

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
        MultiFieldPanel(
            [
                FieldPanel("newsletter_heading"),
                FieldPanel("newsletter_copy"),
                FieldPanel("newsletter_form_action"),
                FieldPanel("newsletter_button_label"),
            ],
            heading="Newsletter",
        ),
    ]


LOGO_CHOICES = [
    ("brand/primary/Logo-07.svg", "Primary Logo 07"),
    ("brand/primary/Logo-08.svg", "Primary Logo 08"),
    ("brand/primary/Logo-09.svg", "Primary Logo 09"),
    ("brand/primary/Logo-10.svg", "Primary Logo 10"),
    ("brand/primary/Logo-11.svg", "Primary Logo 11"),
    ("brand/primary/Logo-12.svg", "Primary Logo 12"),
]

MARK_CHOICES = [
    ("brand/brand_mark/Logo-01.svg", "Mark 01"),
    ("brand/brand_mark/Logo-02.svg", "Mark 02"),
    ("brand/brand_mark/Logo-03.svg", "Mark 03"),
    ("brand/brand_mark/Logo-04.svg", "Mark 04"),
    ("brand/brand_mark/Logo-05.svg", "Mark 05"),
    ("brand/brand_mark/Logo-06.svg", "Mark 06"),
]


@register_setting
class BrandAppearanceSettings(BaseSiteSetting):
    # Asset selection (defaults = your chosen ones)
    logo_light_path = models.CharField(max_length=255, choices=LOGO_CHOICES, default="brand/primary/Logo-08.svg")
    logo_dark_path = models.CharField(max_length=255, choices=LOGO_CHOICES, default="brand/primary/Logo-09.svg")
    mark_light_path = models.CharField(max_length=255, choices=MARK_CHOICES, default="brand/brand_mark/Logo-02.svg")
    mark_dark_path = models.CharField(max_length=255, choices=MARK_CHOICES, default="brand/brand_mark/Logo-03.svg")

    # Theme tokens (hex) — defaults match your tokens.css
    light_bg = ColorField(default="#e5e0d6")
    light_fg = ColorField(default="#261b16")
    light_surface = ColorField(default="#ffffff")
    light_surface_2 = ColorField(default="#f5f2ee")
    light_border = ColorField(default="#b8a693")
    light_muted = ColorField(default="#786050")
    light_heading = ColorField(default="#3d2b1f")
    light_accent = ColorField(default="#3d2b1f")
    light_accent_2 = ColorField(default="#786050")

    dark_bg = ColorField(default="#261b16")
    dark_fg = ColorField(default="#e5e0d6")
    dark_surface = ColorField(default="#3d2b1f")
    dark_surface_2 = ColorField(default="#4d2621")
    dark_border = ColorField(default="#b8a693")
    dark_muted = ColorField(default="#b8a693")
    dark_heading = ColorField(default="#e5e0d6")
    dark_accent = ColorField(default="#b8a693")
    dark_accent_2 = ColorField(default="#786050")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("logo_light_path"),
                FieldPanel("logo_dark_path"),
                FieldPanel("mark_light_path"),
                FieldPanel("mark_dark_path"),
            ],
            heading="Brand assets",
        ),
        MultiFieldPanel(
            [
                FieldPanel("light_bg"),
                FieldPanel("light_fg"),
                FieldPanel("light_surface"),
                FieldPanel("light_surface_2"),
                FieldPanel("light_border"),
                FieldPanel("light_muted"),
                FieldPanel("light_heading"),
                FieldPanel("light_accent"),
                FieldPanel("light_accent_2"),
            ],
            heading="Light theme tokens",
        ),
        MultiFieldPanel(
            [
                FieldPanel("dark_bg"),
                FieldPanel("dark_fg"),
                FieldPanel("dark_surface"),
                FieldPanel("dark_surface_2"),
                FieldPanel("dark_border"),
                FieldPanel("dark_muted"),
                FieldPanel("dark_heading"),
                FieldPanel("dark_accent"),
                FieldPanel("dark_accent_2"),
            ],
            heading="Dark theme tokens",
        ),
    ]

    class Meta:
        verbose_name = "Brand appearance"
