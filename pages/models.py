from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from django.db import models
from django.utils import timezone

from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from taggit.models import TaggedItemBase

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.fields import RichTextField, StreamField
from wagtail.images import get_image_model_string
from wagtail.models import Page

from .blocks import ContactLinks, HomeSections, ModularSections, BlogBody


def _richtext_to_plain_text(html: str) -> str:
    """
    Very small helper for schema extraction (FAQ text).
    """
    if not html:
        return ""
    # quick + safe strip: Wagtail's richtext is limited; JSON-LD doesn't need HTML
    import re

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_faq_schema(pairs: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    if not pairs:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": p["question"],
                "acceptedAnswer": {"@type": "Answer", "text": p["answer"]},
            }
            for p in pairs
            if p.get("question") and p.get("answer")
        ],
    }


# ---------------------------
# Core pages
# ---------------------------

class HomePage(Page):
    sections = StreamField(
        HomeSections(),
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("sections"),
    ]

    parent_page_types: List[str] = ["wagtailcore.Page"]
    subpage_types: List[str] = ["TreatmentsIndexPage", "AboutPage", "ContactPage", "BlogIndexPage", "StandardPage"]

    template = "pages/home_page.html"

    class Meta:
        verbose_name = "Homepage"


class StandardPage(Page):
    body = RichTextField(blank=True, features=["h2", "h3", "bold", "italic", "link", "ul", "ol"])

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    parent_page_types = ["HomePage"]
    subpage_types: List[str] = []

    template = "pages/standard_page.html"

    class Meta:
        verbose_name = "Standard page"


# ---------------------------
# Treatments / menu
# ---------------------------

class TreatmentsIndexPage(Page):
    intro = RichTextField(blank=True, help_text="Optional intro text shown under the title.")
    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    sections = StreamField(
        ModularSections(),
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("sections"),
    ]

    parent_page_types = ["HomePage"]
    subpage_types: List[str] = ["MenuSectionPage"]

    template = "pages/treatments_index_page.html"

    class Meta:
        verbose_name = "Menu index"


class MenuSectionPage(Page):
    intro = RichTextField(blank=True, help_text="Optional editorial intro for this menu section.")
    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    sections = StreamField(
        ModularSections(),
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("sections"),
    ]

    parent_page_types = ["TreatmentsIndexPage"]
    subpage_types: List[str] = ["TreatmentPage"]

    template = "pages/menu_section_page.html"

    class Meta:
        verbose_name = "Menu section"


class TreatmentPage(Page):
    summary = models.TextField(
        blank=True,
        max_length=240,
        help_text="One paragraph summary for the top of the page.",
    )

    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    sections = StreamField(
        ModularSections(),
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("summary"),
        FieldPanel("featured_image"),
        FieldPanel("sections"),
    ]

    parent_page_types = ["MenuSectionPage"]
    subpage_types: List[str] = []

    template = "pages/treatment_page.html"

    class Meta:
        verbose_name = "Treatment page"


# ---------------------------
# About
# ---------------------------

class AboutPage(Page):
    intro = RichTextField(blank=True, help_text="Optional intro shown under the title.")
    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    sections = StreamField(
        ModularSections(),
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("sections"),
        InlinePanel("team_members", label="Team members"),
    ]

    parent_page_types = ["HomePage"]
    subpage_types: List[str] = []

    template = "pages/about_page.html"

    class Meta:
        verbose_name = "About page"


class AboutTeamMember(models.Model):
    page = ParentalKey(AboutPage, on_delete=models.CASCADE, related_name="team_members")
    name = models.CharField(max_length=80)
    role = models.CharField(max_length=80, blank=True)
    experience = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)
    image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
        FieldPanel("experience"),
        FieldPanel("bio"),
        FieldPanel("image"),
    ]

    def __str__(self) -> str:
        return self.name


# ---------------------------
# Blog
# ---------------------------

class BlogIndexPage(Page):
    intro = RichTextField(blank=True, help_text="Optional intro text for the journal landing page.")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    parent_page_types = ["HomePage"]
    subpage_types: List[str] = ["BlogPage"]

    template = "pages/blog_index_page.html"

    class Meta:
        verbose_name = "Blog index"

    def get_posts(self):
        return BlogPage.objects.child_of(self).live().public().order_by("-date")


class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey(
        "BlogPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class BlogPage(Page):
    date = models.DateField(default=timezone.now)

    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    excerpt = models.TextField(
        blank=True,
        max_length=240,
        help_text="Short summary used on listings and as meta description fallback.",
    )

    body = StreamField(
        BlogBody(),
        use_json_field=True,
        blank=True,
    )

    tags = ClusterTaggableManager(through=BlogPageTag, blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("date"),
                FieldPanel("featured_image"),
                FieldPanel("excerpt"),
                FieldPanel("tags"),
            ],
            heading="Post details",
        ),
        FieldPanel("body"),
    ]

    parent_page_types = ["BlogIndexPage"]
    subpage_types: List[str] = []

    template = "pages/blog_page.html"

    class Meta:
        verbose_name = "Blog post"

    def get_faq_qa_pairs(self) -> List[Dict[str, str]]:
        pairs: List[Dict[str, str]] = []
        if not self.body:
            return pairs

        for block in self.body:
            if block.block_type != "faq":
                continue
            faq_val = block.value
            for item in faq_val.get("items", []):
                q = (item.get("question") or "").strip()
                a_html = item.get("answer") or ""
                a = _richtext_to_plain_text(a_html)
                if q and a:
                    pairs.append({"question": q, "answer": a})

        return pairs

    def get_structured_data(self, request) -> List[Dict[str, Any]]:
        url = request.build_absolute_uri(self.get_url(request=request))
        data: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.seo_title or self.title,
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "datePublished": self.date.isoformat(),
        }

        if self.last_published_at:
            data["dateModified"] = self.last_published_at.date().isoformat()

        if self.excerpt:
            data["description"] = self.excerpt

        payloads: List[Dict[str, Any]] = [data]

        faq = _build_faq_schema(self.get_faq_qa_pairs())
        if faq:
            payloads.append(faq)

        return payloads


# ---------------------------
# Contact (email form page)
# ---------------------------

class ContactPageFormField(AbstractFormField):
    page = ParentalKey("ContactPage", on_delete=models.CASCADE, related_name="form_fields")


class ContactPage(AbstractEmailForm):
    """
    Contact page with Wagtail-managed enquiry form.

    IMPORTANT:
    Some Wagtail versions do NOT include `thank_you_text` on AbstractEmailForm.
    We define it here explicitly to keep admin panels + templates stable.
    """

    intro = RichTextField(
        blank=True,
        features=["bold", "italic", "link", "ul", "ol"],
        help_text="Optional short intro shown above the form.",
    )

    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )

    map_embed_url = models.URLField(
        blank=True,
        max_length=2000,
        help_text="Optional Google Maps embed URL (iframe src). Paste only the iframe src value.",
    )

    booking_links = StreamField(
        ContactLinks(),
        use_json_field=True,
        blank=True,
        help_text="Buttons to socials / booking portals / external destinations.",
    )

    thank_you_text = RichTextField(
        blank=True,
        features=["bold", "italic", "link", "ul", "ol"],
        help_text="Shown after successful form submission.",
    )

    content_panels = AbstractEmailForm.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("map_embed_url"),
        FieldPanel("booking_links"),
        MultiFieldPanel(
            [
                InlinePanel("form_fields", label="Form fields"),
            ],
            heading="Enquiry form fields",
        ),
        MultiFieldPanel(
            [
                FieldPanel("to_address"),
                FieldPanel("from_address"),
                FieldPanel("subject"),
            ],
            heading="Email settings",
        ),
        FieldPanel("thank_you_text"),
    ]

    parent_page_types = ["HomePage"]
    subpage_types: List[str] = ["StandardPage"]

    template = "pages/contact_page.html"
    landing_page_template = "pages/contact_page_landing.html"

    class Meta:
        verbose_name = "Contact page"
