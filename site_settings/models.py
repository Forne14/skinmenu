from django.db import models

from colorfield.fields import ColorField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField

from .blocks import NavLinkBlock


@register_setting
class GlobalSiteSettings(BaseSiteSetting):
    clinic_name = models.CharField(max_length=120, default="SKINMENU")
    address = models.TextField(blank=True)

    # NOTE: kept in model for backwards compatibility, but requirements want these unused.
    opening_hours = models.TextField(blank=True, help_text="E.g. Mon–Fri 10:00–19:00")
    phone = models.CharField(max_length=50, blank=True)

    email = models.EmailField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)

    google_maps_url = models.URLField(
        blank=True,
        help_text="Optional: link to Google Maps location (for footer + contact).",
    )

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
                FieldPanel("email"),
                FieldPanel("google_maps_url"),
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
        MultiFieldPanel(
            [
                FieldPanel("opening_hours"),
                FieldPanel("phone"),
            ],
            heading="Legacy fields (not used on site)",
            help_text="Client preference is to avoid showing phone/opening hours. Keep for reference only.",
        ),
    ]


@register_setting
class NavigationSettings(BaseSiteSetting):
    primary_links = StreamField(
        [("link", NavLinkBlock())],
        use_json_field=True,
        blank=True,
        help_text="Top-level navigation links.",
    )

    menu_label = models.CharField(max_length=30, default="The Menu", blank=True)
    menu_links = StreamField(
        [("link", NavLinkBlock())],
        use_json_field=True,
        blank=True,
        help_text="Dropdown links under 'The Menu'.",
    )

    header_cta = StreamField(
        [("link", NavLinkBlock())],
        use_json_field=True,
        blank=True,
        max_num=1,
        help_text="Optional single CTA button in header (e.g. Enquire).",
    )

    footer_links = StreamField(
        [("link", NavLinkBlock())],
        use_json_field=True,
        blank=True,
        help_text="Footer links column (e.g. About, Journal, Contact, Privacy).",
    )

    panels = [
        MultiFieldPanel([FieldPanel("primary_links")], heading="Primary navigation"),
        MultiFieldPanel(
            [FieldPanel("menu_label"), FieldPanel("menu_links")],
            heading="Dropdown: The Menu",
        ),
        MultiFieldPanel([FieldPanel("header_cta")], heading="Header CTA"),
        MultiFieldPanel([FieldPanel("footer_links")], heading="Footer links"),
    ]

    class Meta:
        verbose_name = "Navigation"


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
class AnalyticsSettings(BaseSiteSetting):
    ga4_measurement_id = models.CharField(
        max_length=32,
        blank=True,
        help_text="GA4 Measurement ID (e.g. G-XXXXXXX). Loaded only with analytics consent.",
    )
    meta_pixel_id = models.CharField(
        max_length=32,
        blank=True,
        help_text="Meta Pixel ID. Loaded only with marketing consent.",
    )

    panels = [
        FieldPanel("ga4_measurement_id"),
        FieldPanel("meta_pixel_id"),
    ]

    class Meta:
        verbose_name = "Analytics"



@register_setting
class BrandAppearanceSettings(BaseSiteSetting):
    logo_light_path = models.CharField(max_length=255, choices=LOGO_CHOICES, default="brand/primary/Logo-08.svg")
    logo_dark_path = models.CharField(max_length=255, choices=LOGO_CHOICES, default="brand/primary/Logo-09.svg")
    mark_light_path = models.CharField(max_length=255, choices=MARK_CHOICES, default="brand/brand_mark/Logo-02.svg")
    mark_dark_path = models.CharField(max_length=255, choices=MARK_CHOICES, default="brand/brand_mark/Logo-03.svg")

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
