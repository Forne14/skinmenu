from wagtail import blocks
from wagtail.blocks import PageChooserBlock
from wagtail.images.blocks import ImageChooserBlock


class LinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=40)
    url = blocks.URLBlock(required=True)

    class Meta:
        icon = "link"
        label = "Link"


class ContactLinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=40)
    url = blocks.URLBlock(required=True)
    note = blocks.CharBlock(required=False, max_length=60, help_text="Optional small helper text.")

    class Meta:
        icon = "link"
        label = "Button link"


class ContactLinks(blocks.StreamBlock):
    link = ContactLinkBlock()

    class Meta:
        label = "Booking links"
        icon = "link"


class HeroBlock(blocks.StructBlock):
    headline = blocks.CharBlock(required=True, max_length=80, default="Your best skin, on the menu")
    subheadline = blocks.TextBlock(required=False, max_length=240)
    primary_cta = LinkBlock(required=False)

    cta_position = blocks.ChoiceBlock(
        required=True,
        default="bottom_left",
        choices=[
            ("bottom_left", "Bottom left"),
            ("center", "Center"),
            ("bottom_right", "Bottom right"),
            ("top_left", "Top left"),
            ("top_right", "Top right"),
        ],
        help_text="Where the hero text + CTA sits on the image.",
    )

    hero_images = blocks.ListBlock(
        ImageChooserBlock(required=True),
        required=False,
        help_text="Add 1 image for a static hero. Add 2+ for a carousel.",
    )

    class Meta:
        icon = "image"
        label = "Hero"
        template = "pages/blocks/hero.html"


# ---------------------------
# Legacy homepage block (back-compat)
# ---------------------------

class FeaturedMenuLegacyBlock(blocks.StructBlock):
    """
    Backwards-compatible homepage block used by older DB content.
    This matches pages/templates/pages/blocks/featured_menu.html
    """
    heading = blocks.CharBlock(required=False, max_length=80, default="Treatments")
    intro = blocks.TextBlock(required=False, max_length=220)

    featured_pages = blocks.ListBlock(
        PageChooserBlock(required=False),
        required=False,
        help_text="Legacy: pick pages to feature on the homepage.",
    )

    cta_label = blocks.CharBlock(required=False, max_length=30, default="See full menu")
    cta_page = PageChooserBlock(required=False, help_text="Typically the /menu page.")

    def to_python(self, value):
        """
        Older seeds sometimes stored featured_pages as a list of ints.
        Normalize to list of PageChooser values.
        """
        if isinstance(value, dict) and "featured_pages" in value and isinstance(value["featured_pages"], list):
            fixed = []
            for v in value["featured_pages"]:
                fixed.append(v)
            value["featured_pages"] = fixed
        return super().to_python(value)

    class Meta:
        icon = "list-ul"
        label = "Featured menu (legacy)"
        template = "pages/blocks/featured_menu.html"


class TreatmentTileBlock(blocks.StructBlock):
    page = PageChooserBlock(required=True)
    image = ImageChooserBlock(required=False, help_text="Optional. If empty, a clean placeholder will be shown.")
    blurb = blocks.CharBlock(required=False, max_length=140, help_text="Optional short line.")

    def to_python(self, value):
        if isinstance(value, int):
            value = {"page": value, "image": None, "blurb": ""}
        return super().to_python(value)

    def bulk_to_python(self, values):
        normalized = []
        for v in values:
            if isinstance(v, int):
                normalized.append({"page": v, "image": None, "blurb": ""})
            else:
                normalized.append(v)
        return super().bulk_to_python(normalized)

    class Meta:
        icon = "doc-empty-inverse"
        label = "Treatment tile"


class TreatmentsGridBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=80, default="Treatments")
    intro = blocks.TextBlock(required=False, max_length=220)

    items = blocks.ListBlock(
        TreatmentTileBlock(),
        min_num=3,
        max_num=18,
        help_text="Add treatment/category tiles. Each can have an optional image.",
    )

    cta_label = blocks.CharBlock(required=False, max_length=30, default="See full menu")
    cta_page = PageChooserBlock(required=False, help_text="Typically the /menu page.")

    class Meta:
        icon = "list-ul"
        label = "Treatments carousel"
        template = "pages/blocks/treatments_grid.html"


class TextImageBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, max_length=40)
    heading = blocks.CharBlock(required=True, max_length=80)
    body = blocks.RichTextBlock(required=True, features=["bold", "italic", "link", "ul", "ol"])
    image = ImageChooserBlock(required=False)
    image_position = blocks.ChoiceBlock(choices=[("left", "Left"), ("right", "Right")], default="right", required=True)

    class Meta:
        icon = "doc-full"
        label = "Text + Image"
        template = "pages/blocks/text_image.html"


class ReviewItemBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True, max_length=420)
    author = blocks.CharBlock(required=True, max_length=60)
    source = blocks.CharBlock(required=False, max_length=60)

    class Meta:
        icon = "openquote"
        label = "Review"


class ReviewsSliderBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=60, default="Client reviews")
    reviews = blocks.ListBlock(ReviewItemBlock(), required=False, max_num=20)

    class Meta:
        icon = "group"
        label = "Reviews carousel"
        template = "pages/blocks/reviews_slider.html"


class CTABlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=True, max_length=80)
    body = blocks.TextBlock(required=False, max_length=240)
    primary_cta = LinkBlock(required=True)
    secondary_cta = LinkBlock(required=False)

    def to_python(self, value):
        if isinstance(value, dict):
            if "primary" in value and "primary_cta" not in value:
                value["primary_cta"] = value.get("primary")
            if "secondary" in value and "secondary_cta" not in value:
                value["secondary_cta"] = value.get("secondary")
            if "text" in value and "body" not in value:
                value["body"] = value.get("text")
        return super().to_python(value)

    class Meta:
        icon = "tick"
        label = "CTA"
        template = "pages/blocks/cta.html"


class HomeSections(blocks.StreamBlock):
    hero = HeroBlock()
    # Legacy block retained so older DB content doesn't break
    featured_menu = FeaturedMenuLegacyBlock()

    treatments = TreatmentsGridBlock()
    text_image = TextImageBlock()
    reviews_slider = ReviewsSliderBlock()
    cta = CTABlock()

    class Meta:
        label = "Homepage sections"
        icon = "list-ul"


# ---------------------------
# Modular blocks for inner pages
# ---------------------------

class RichTextSectionBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, max_length=40)
    heading = blocks.CharBlock(required=True, max_length=90)
    body = blocks.RichTextBlock(required=True, features=["bold", "italic", "link", "ul", "ol"])

    class Meta:
        icon = "doc-full"
        label = "Text section"
        template = "pages/blocks/rich_text_section.html"


class KeyFactsItemBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=40)
    value = blocks.CharBlock(required=True, max_length=80)

    class Meta:
        icon = "list-ul"
        label = "Fact"


class KeyFactsBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, max_length=40)
    heading = blocks.CharBlock(required=True, max_length=80, default="Key facts")
    facts = blocks.ListBlock(KeyFactsItemBlock(), min_num=1, max_num=8)

    class Meta:
        icon = "list-ul"
        label = "Key facts"
        template = "pages/blocks/key_facts.html"


class StepItemBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True, max_length=60)
    text = blocks.RichTextBlock(required=True, features=["bold", "italic", "link", "ul", "ol"])

    class Meta:
        icon = "form"
        label = "Step"


class StepsBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, max_length=40)
    heading = blocks.CharBlock(required=True, max_length=80, default="What to expect")
    steps = blocks.ListBlock(StepItemBlock(), min_num=1, max_num=8)

    class Meta:
        icon = "form"
        label = "Steps"
        template = "pages/blocks/steps.html"


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock(required=True, max_length=160)
    answer = blocks.RichTextBlock(required=True, features=["bold", "italic", "link", "ul", "ol"])

    class Meta:
        icon = "help"
        label = "FAQ item"


class FAQBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, max_length=40)
    heading = blocks.CharBlock(required=True, max_length=80, default="Frequently asked questions")
    items = blocks.ListBlock(FAQItemBlock(), min_num=1, max_num=20)

    class Meta:
        icon = "help"
        label = "FAQs"
        template = "pages/blocks/faq.html"


class ModularSections(blocks.StreamBlock):
    rich_text_section = RichTextSectionBlock()
    text_image = TextImageBlock()
    key_facts = KeyFactsBlock()
    steps = StepsBlock()
    faq = FAQBlock()
    cta = CTABlock()

    class Meta:
        label = "Sections"
        icon = "list-ul"


# ---------------------------
# Blog blocks
# ---------------------------

class PullQuoteBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True, max_length=280)
    attribution = blocks.CharBlock(required=False, max_length=80)

    class Meta:
        icon = "openquote"
        label = "Pull quote"
        template = "pages/blocks/pull_quote.html"


class BlogImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    caption = blocks.CharBlock(required=False, max_length=120)

    class Meta:
        icon = "image"
        label = "Image"
        template = "pages/blocks/blog_image.html"


class BlogBody(blocks.StreamBlock):
    rich_text = blocks.RichTextBlock(features=["h2", "h3", "bold", "italic", "link", "ul", "ol"])
    image = BlogImageBlock()
    pull_quote = PullQuoteBlock()
    faq = FAQBlock()
    cta = CTABlock()

    class Meta:
        label = "Blog body"
        icon = "doc-full"
