from django.db import models
from django.conf import settings
from django import forms

from colorfield.fields import ColorField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField

from pathlib import Path
import glob

from .blocks import NavLinkBlock


# ---------------------------------------------------------------------
# Global settings
# ---------------------------------------------------------------------
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
        help_text="Optional: link to Google Maps location (normal URL).",
    )

    # New canonical embed SRC for footer/contact iframe rendering.
    # Editors paste only the iframe src URL (not the full <iframe> HTML).
    google_maps_embed_url = models.URLField(
        blank=True,
        max_length=2000,
        help_text="Paste the Google Maps iframe *src* URL (not the full iframe tag). Used to render an embed iframe.",
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
                FieldPanel("phone"),
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
            heading="Social",
        ),
        MultiFieldPanel(
            [
                FieldPanel("google_maps_url"),
                FieldPanel("google_maps_embed_url"),
            ],
            heading="Google Maps",
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

    class Meta:
        verbose_name = "Global"


# ---------------------------------------------------------------------
# Navigation settings
# ---------------------------------------------------------------------
@register_setting
class NavigationSettings(BaseSiteSetting):
    primary_links = StreamField(
        [("link", NavLinkBlock())],
        blank=True,
        use_json_field=True,
        help_text="Top-level navigation links.",
    )

    menu_label = models.CharField(max_length=30, blank=True, default="The Menu")

    menu_links = StreamField(
        [("link", NavLinkBlock())],
        blank=True,
        use_json_field=True,
        help_text="Dropdown links under 'The Menu'.",
    )

    header_cta = StreamField(
        [("link", NavLinkBlock())],
        blank=True,
        use_json_field=True,
        help_text="Optional single CTA button in header (e.g. Enquire).",
    )

    footer_links = StreamField(
        [("link", NavLinkBlock())],
        blank=True,
        use_json_field=True,
        help_text="Footer links column (e.g. About, Journal, Contact, Privacy).",
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("primary_links"),
                FieldPanel("menu_label"),
                FieldPanel("menu_links"),
                FieldPanel("header_cta"),
            ],
            heading="Header navigation",
        ),
        MultiFieldPanel(
            [
                FieldPanel("footer_links"),
            ],
            heading="Footer navigation",
        ),
    ]

    class Meta:
        verbose_name = "Navigation"


# ---------------------------------------------------------------------
# Analytics settings (used by cookie-consent logic + bootstrap_dev)
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# Brand appearance (used by tokens + base templates + bootstrap_dev)
# ---------------------------------------------------------------------
LOGO_CHOICES = [
    ("brand/primary/Logo-07.svg", "Primary Logo 07"),
    ("brand/primary/Logo-08.svg", "Primary Logo 08"),
    ("brand/primary/Logo-09.svg", "Primary Logo 09"),
]

MARK_CHOICES = [
    ("brand/brand_mark/Logo-01.svg", "Brand Mark 01"),
    ("brand/brand_mark/Logo-02.svg", "Brand Mark 02"),
    ("brand/brand_mark/Logo-03.svg", "Brand Mark 03"),
]


def _static_dir() -> Path:
    """
    Returns a filesystem path to a static directory we can scan for SVGs.

    Prefers BASE_DIR/config/static (matches your repo layout),
    then falls back to the first STATICFILES_DIRS entry.
    """
    base_dir = Path(getattr(settings, "BASE_DIR", Path(".")))
    preferred = base_dir / "config" / "static"
    if preferred.exists():
        return preferred

    staticfiles_dirs = getattr(settings, "STATICFILES_DIRS", []) or []
    if staticfiles_dirs:
        return Path(staticfiles_dirs[0])

    # Last resort: project root
    return base_dir


def _svg_choices_in_static(rel_glob: str) -> list[tuple[str, str]]:
    """
    Build (static_path, label) choices by scanning the filesystem.
    rel_glob should be relative to a static root (e.g. 'brand/secondary/*.svg').
    Stored value will be the *static path* (e.g. 'brand/secondary/Logo-16.svg').
    """
    static_root = _static_dir()
    pattern = str(static_root / rel_glob)
    found = sorted(glob.glob(pattern))
    choices: list[tuple[str, str]] = []

    for abs_path in found:
        p = Path(abs_path)
        try:
            rel = p.relative_to(static_root).as_posix()
        except ValueError:
            continue
        choices.append((rel, p.name))

    return choices


def _secondary_logo_choices() -> list[tuple[str, str]]:
    # Scans config/static/brand/secondary/*.svg
    return _svg_choices_in_static("brand/secondary/*.svg")


@register_setting
class BrandAppearanceSettings(BaseSiteSetting):
    logo_light_path = models.CharField(max_length=255, choices=LOGO_CHOICES, default="brand/primary/Logo-08.svg")
    logo_dark_path = models.CharField(max_length=255, choices=LOGO_CHOICES, default="brand/primary/Logo-09.svg")
    mark_light_path = models.CharField(max_length=255, choices=MARK_CHOICES, default="brand/brand_mark/Logo-02.svg")
    mark_dark_path = models.CharField(max_length=255, choices=MARK_CHOICES, default="brand/brand_mark/Logo-03.svg")

    # Footer logo variant selection
    FOOTER_LOGO_VARIANT_PRIMARY = "primary"
    FOOTER_LOGO_VARIANT_SECONDARY = "secondary"
    FOOTER_LOGO_VARIANT_MARK = "mark"

    FOOTER_LOGO_VARIANT_CHOICES = [
        (FOOTER_LOGO_VARIANT_PRIMARY, "Primary"),
        (FOOTER_LOGO_VARIANT_SECONDARY, "Secondary"),
        (FOOTER_LOGO_VARIANT_MARK, "Mark"),
    ]

    footer_logo_variant = models.CharField(
        max_length=20,
        choices=FOOTER_LOGO_VARIANT_CHOICES,
        default=FOOTER_LOGO_VARIANT_PRIMARY,
        help_text="Logo variant to show in the footer.",
    )

    secondary_logo_light_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Static path under /static (e.g. 'brand/secondary/Logo-16.svg'). Used on light theme.",
    )

    secondary_logo_dark_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="Static path under /static (e.g. 'brand/secondary/Logo-16.svg'). Used on dark theme.",
    )

    # Typography (site-wide)
    body_font_size_px = models.PositiveSmallIntegerField(
        default=16,
        help_text="Base body font size in pixels (default 16).",
    )
    body_font_weight = models.PositiveSmallIntegerField(
        default=400,
        help_text="Work Sans variable font weight for body copy (e.g. 300–700). Default 400.",
    )

    heading_font_weight = models.PositiveSmallIntegerField(
        default=300,
        help_text="Heading font weight (Koh Santepheap). Default 300 to match current styling.",
    )

    ui_font_size_px = models.PositiveSmallIntegerField(
        default=15,
        help_text="Base UI font size in pixels for buttons/nav/labels (default 15).",
    )
    ui_font_weight = models.PositiveSmallIntegerField(
        default=300,
        help_text="UI font weight for components (default 300 to match nav/labels/headings).",
    )

    # Background texture (CSS-only “paper” grain)
    paper_texture_enabled = models.BooleanField(
        default=True,
        help_text="Adds a subtle paper-like texture to the site background (works in light + dark mode).",
    )
    paper_texture_strength = models.PositiveSmallIntegerField(
        default=100,
        help_text="Texture strength (0–200). 100 is subtle and recommended.",
    )

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
                FieldPanel("body_font_size_px"),
                FieldPanel("body_font_weight"),
                FieldPanel("heading_font_weight"),
                FieldPanel("ui_font_size_px"),
                FieldPanel("ui_font_weight"),
            ],
            heading="Typography",
        ),
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
                FieldPanel("secondary_logo_light_path", widget=forms.Select(choices=_secondary_logo_choices())),
                FieldPanel("secondary_logo_dark_path", widget=forms.Select(choices=_secondary_logo_choices())),
            ],
            heading="Secondary logo",
        ),
        MultiFieldPanel(
            [
                FieldPanel("footer_logo_variant"),
            ],
            heading="Footer",
        ),
        MultiFieldPanel(
            [
                FieldPanel("paper_texture_enabled"),
                FieldPanel("paper_texture_strength"),
            ],
            heading="Background texture",
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
