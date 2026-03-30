from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.documents import get_document_model_string
from wagtail.fields import RichTextField
from wagtail.images import get_image_model_string
from wagtail.snippets.models import register_snippet


MEDIA_USAGE_CHOICES = [
    ("hero", "Hero"),
    ("carousel", "Carousel"),
    ("gallery", "Gallery"),
]

MEDIA_POSITION_CHOICES = [
    ("left", "Left"),
    ("right", "Right"),
]

PLAYBACK_RATE_CHOICES = [
    ("0.75", "0.75x (slow)"),
    ("1.0", "1.0x (normal)"),
    ("1.25", "1.25x (fast)"),
    ("1.5", "1.5x (fast)"),
]

CONTENT_BLOCK_TYPE_CHOICES = [
    ("hero", "Hero"),
    ("rich_text", "Rich text"),
    ("text_media", "Text + media"),
    ("cta", "CTA"),
    ("faq", "FAQ"),
    ("steps", "Steps"),
    ("reviews", "Reviews"),
    ("products", "Products"),
]


@register_snippet
class ClinicLocation(models.Model):
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    postcode = models.CharField(max_length=40, blank=True)
    country = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    hours = models.TextField(blank=True)
    map_url = models.URLField(blank=True)
    map_embed_url = models.URLField(blank=True, max_length=2000)
    timezone = models.CharField(max_length=60, blank=True)
    is_primary = models.BooleanField(default=False)

    panels = [
        FieldPanel("name"),
        FieldPanel("address"),
        MultiFieldPanel(
            [
                FieldPanel("city"),
                FieldPanel("postcode"),
                FieldPanel("country"),
            ],
            heading="Location",
        ),
        MultiFieldPanel(
            [
                FieldPanel("phone"),
                FieldPanel("email"),
                FieldPanel("hours"),
            ],
            heading="Contact",
        ),
        MultiFieldPanel(
            [
                FieldPanel("map_url"),
                FieldPanel("map_embed_url"),
            ],
            heading="Map",
        ),
        FieldPanel("timezone"),
        FieldPanel("is_primary"),
    ]

    class Meta:
        verbose_name = "Clinic location"
        verbose_name_plural = "Clinic locations"

    def __str__(self) -> str:
        return self.name


@register_snippet
class SocialProfile(models.Model):
    location = models.ForeignKey(
        ClinicLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="social_profiles",
    )
    platform = models.CharField(max_length=40)
    url = models.URLField()
    handle = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    panels = [
        FieldPanel("location"),
        FieldPanel("platform"),
        FieldPanel("url"),
        FieldPanel("handle"),
        FieldPanel("is_active"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "platform"]
        verbose_name = "Social profile"
        verbose_name_plural = "Social profiles"

    def __str__(self) -> str:
        return self.platform


@register_snippet
class Treatment(ClusterableModel):
    """
    Top-level treatment (Lasers, Fillers, Botox, etc.).
    This maps to MenuSectionPage and owns the option list.
    """
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    summary = models.TextField(blank=True, max_length=300)
    long_description = RichTextField(blank=True)
    featured_image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    primary_location = models.ForeignKey(
        ClinicLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="treatments",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("summary"),
        FieldPanel("long_description"),
        FieldPanel("featured_image"),
        MultiFieldPanel(
            [
                FieldPanel("primary_location"),
                FieldPanel("sort_order"),
                FieldPanel("is_active"),
            ],
            heading="Status",
        ),
        InlinePanel("content_blocks", label="Content blocks"),
        InlinePanel("options", label="Options"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Treatment"
        verbose_name_plural = "Treatments"

    def __str__(self) -> str:
        return self.name


@register_snippet
class TreatmentOption(ClusterableModel):
    """
    Option/variant under a treatment (e.g. PicoGenesis under Lasers).
    """
    treatment = ParentalKey(
        Treatment,
        on_delete=models.CASCADE,
        related_name="options",
    )
    name = models.CharField(max_length=160)
    summary = models.TextField(blank=True, max_length=300)
    long_description = RichTextField(blank=True)
    featured_image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    panels = [
        FieldPanel("treatment"),
        FieldPanel("name"),
        FieldPanel("summary"),
        FieldPanel("long_description"),
        FieldPanel("featured_image"),
        MultiFieldPanel(
            [
                FieldPanel("sort_order"),
                FieldPanel("is_active"),
            ],
            heading="Status",
        ),
        InlinePanel("facts", label="Facts"),
        InlinePanel("prices", label="Prices"),
        InlinePanel("media", label="Media"),
        InlinePanel("faqs", label="FAQs"),
        InlinePanel("steps", label="Steps"),
        InlinePanel("content_blocks", label="Content blocks"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Treatment option"
        verbose_name_plural = "Treatment options"

    def __str__(self) -> str:
        return self.name


class TreatmentOptionFact(models.Model):
    option = ParentalKey(
        TreatmentOption,
        on_delete=models.CASCADE,
        related_name="facts",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=60)
    value = models.CharField(max_length=160)

    panels = [
        FieldPanel("label"),
        FieldPanel("value"),
    ]

    class Meta:
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return f"{self.label}: {self.value}"


class TreatmentPrice(models.Model):
    option = ParentalKey(
        TreatmentOption,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=80, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, default="GBP")
    price_text = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    targets = models.TextField(
        blank=True,
        help_text="One per line. Used to show the treatment targets list.",
    )
    notes = models.CharField(max_length=240, blank=True)

    panels = [
        FieldPanel("label"),
        FieldPanel("amount"),
        FieldPanel("currency"),
        FieldPanel("price_text"),
        FieldPanel("description"),
        FieldPanel("targets"),
        FieldPanel("notes"),
    ]

    class Meta:
        ordering = ["sort_order"]

    def clean(self) -> None:
        super().clean()
        if self.amount is None and not (self.price_text or "").strip():
            raise ValidationError("Provide an amount or a price label.")

    def display_price(self) -> str:
        if (self.price_text or "").strip():
            return self.price_text
        if self.amount is None:
            return ""
        symbol = "\u00a3" if self.currency.upper() == "GBP" else self.currency
        return f"{symbol}{self.amount:,.2f}"

    def __str__(self) -> str:
        return self.label or self.display_price() or "Price"


class TreatmentMedia(models.Model):
    option = ParentalKey(
        TreatmentOption,
        on_delete=models.CASCADE,
        related_name="media",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    usage = models.CharField(max_length=20, choices=MEDIA_USAGE_CHOICES, default="hero")
    image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    video = models.ForeignKey(
        get_document_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    alt_text = models.CharField(max_length=160, blank=True)
    pos_x = models.PositiveSmallIntegerField(default=50)
    pos_y = models.PositiveSmallIntegerField(default=50)
    loop = models.BooleanField(default=True)
    playback_rate = models.CharField(max_length=8, choices=PLAYBACK_RATE_CHOICES, default="1.0")

    panels = [
        FieldPanel("usage"),
        FieldPanel("image"),
        FieldPanel("video"),
        FieldPanel("alt_text"),
        MultiFieldPanel(
            [
                FieldPanel("pos_x"),
                FieldPanel("pos_y"),
            ],
            heading="Media focus",
        ),
        MultiFieldPanel(
            [
                FieldPanel("loop"),
                FieldPanel("playback_rate"),
            ],
            heading="Video",
        ),
    ]

    class Meta:
        ordering = ["sort_order"]

    def clean(self) -> None:
        super().clean()
        if not self.image and not self.video:
            raise ValidationError("Select an image or a video.")


class TreatmentFAQ(models.Model):
    option = ParentalKey(
        TreatmentOption,
        on_delete=models.CASCADE,
        related_name="faqs",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    question = models.CharField(max_length=200)
    answer = RichTextField()

    panels = [
        FieldPanel("question"),
        FieldPanel("answer"),
    ]

    class Meta:
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return self.question


class TreatmentStep(models.Model):
    option = ParentalKey(
        TreatmentOption,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=120)
    body = RichTextField()

    panels = [
        FieldPanel("title"),
        FieldPanel("body"),
    ]

    class Meta:
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return self.title


@register_snippet
class ContentBlock(ClusterableModel):
    block_type = models.CharField(max_length=20, choices=CONTENT_BLOCK_TYPE_CHOICES)
    eyebrow = models.CharField(max_length=60, blank=True)
    heading = models.CharField(max_length=120, blank=True)
    subheading = models.CharField(max_length=120, blank=True)
    body = RichTextField(blank=True)
    primary_cta_label = models.CharField(max_length=60, blank=True)
    primary_cta_url = models.URLField(blank=True)
    secondary_cta_label = models.CharField(max_length=60, blank=True)
    secondary_cta_url = models.URLField(blank=True)
    media_image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    media_video = models.ForeignKey(
        get_document_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    media_position = models.CharField(max_length=10, choices=MEDIA_POSITION_CHOICES, default="right")
    loop = models.BooleanField(default=True)
    playback_rate = models.CharField(max_length=8, choices=PLAYBACK_RATE_CHOICES, default="1.0")

    panels = [
        FieldPanel("block_type"),
        FieldPanel("eyebrow"),
        FieldPanel("heading"),
        FieldPanel("subheading"),
        FieldPanel("body"),
        MultiFieldPanel(
            [
                FieldPanel("primary_cta_label"),
                FieldPanel("primary_cta_url"),
                FieldPanel("secondary_cta_label"),
                FieldPanel("secondary_cta_url"),
            ],
            heading="CTA",
        ),
        MultiFieldPanel(
            [
                FieldPanel("media_image"),
                FieldPanel("media_video"),
                FieldPanel("media_position"),
                FieldPanel("loop"),
                FieldPanel("playback_rate"),
            ],
            heading="Media",
        ),
        InlinePanel("items", label="Items"),
    ]

    class Meta:
        verbose_name = "Content block"
        verbose_name_plural = "Content blocks"

    def __str__(self) -> str:
        return self.heading or self.block_type


class ContentBlockItem(models.Model):
    block = ParentalKey(ContentBlock, on_delete=models.CASCADE, related_name="items")
    sort_order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=120, blank=True)
    body = RichTextField(blank=True)
    label = models.CharField(max_length=80, blank=True)
    value = models.CharField(max_length=160, blank=True)
    url = models.URLField(blank=True)
    image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    video = models.ForeignKey(
        get_document_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    price_text = models.CharField(max_length=60, blank=True)
    cta_label = models.CharField(max_length=60, blank=True)
    cta_url = models.URLField(blank=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("body"),
        FieldPanel("label"),
        FieldPanel("value"),
        FieldPanel("url"),
        FieldPanel("image"),
        FieldPanel("video"),
        FieldPanel("price_text"),
        FieldPanel("cta_label"),
        FieldPanel("cta_url"),
    ]

    class Meta:
        ordering = ["sort_order"]


class TreatmentContentBlock(models.Model):
    treatment = ParentalKey(Treatment, on_delete=models.CASCADE, related_name="content_blocks")
    sort_order = models.PositiveSmallIntegerField(default=0)
    block = models.ForeignKey(ContentBlock, on_delete=models.CASCADE, related_name="treatment_links")

    panels = [
        FieldPanel("block"),
    ]

    class Meta:
        ordering = ["sort_order"]


class TreatmentOptionContentBlock(models.Model):
    option = ParentalKey(
        TreatmentOption,
        on_delete=models.CASCADE,
        related_name="content_blocks",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    block = models.ForeignKey(ContentBlock, on_delete=models.CASCADE, related_name="option_links")

    panels = [
        FieldPanel("block"),
    ]

    class Meta:
        ordering = ["sort_order"]


@register_snippet
class Review(models.Model):
    quote = models.TextField(max_length=420)
    author = models.CharField(max_length=80)
    source = models.CharField(max_length=80, blank=True)
    link = models.URLField(blank=True)
    rating = models.PositiveSmallIntegerField(blank=True, null=True)
    location = models.ForeignKey(
        ClinicLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviews",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    panels = [
        FieldPanel("quote"),
        FieldPanel("author"),
        FieldPanel("source"),
        FieldPanel("link"),
        FieldPanel("rating"),
        FieldPanel("location"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "author"]

    def __str__(self) -> str:
        return f"{self.author}"


@register_snippet
class TeamMember(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    experience = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    location = models.ForeignKey(
        ClinicLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="team_members",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
        FieldPanel("experience"),
        FieldPanel("bio"),
        FieldPanel("photo"),
        FieldPanel("location"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name
