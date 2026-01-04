from wagtail import blocks
from wagtail.blocks import PageChooserBlock
from wagtail.images.blocks import ImageChooserBlock


class LinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=40)
    url = blocks.URLBlock(required=True)

    class Meta:
        icon = "link"
        label = "Link"


class HeroBlock(blocks.StructBlock):
    headline = blocks.CharBlock(
        required=True,
        max_length=80,
        default="Your best skin, on the menu",
    )
    subheadline = blocks.TextBlock(required=False, max_length=240)

    # Single CTA only
    primary_cta = LinkBlock(required=False)

    # CTA overlay position options
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

    # 1+ images, becomes carousel if >1
    hero_images = blocks.ListBlock(
        ImageChooserBlock(required=True),
        required=False,
        help_text="Add 1 image for a static hero. Add 2+ for a carousel.",
    )

    class Meta:
        icon = "image"
        label = "Hero"
        template = "pages/blocks/hero.html"


class TreatmentTileBlock(blocks.StructBlock):
    """
    Backward-compatible tile.

    Old DB shape (before we added images):
      items: [12, 34, 56]  # page IDs as ints

    New shape:
      items: [{"page": 12, "image": 99, "blurb": "..."}, ...]

    We accept the old int form and convert it on-the-fly so the site + admin don't crash.
    """

    page = PageChooserBlock(required=True)
    image = ImageChooserBlock(
        required=False,
        help_text="Optional. If empty, a clean placeholder will be shown."
    )
    blurb = blocks.CharBlock(
        required=False,
        max_length=140,
        help_text="Optional short line (e.g. 'Enhance your natural features')."
    )

    def to_python(self, value):
        # If old content stored as a bare page ID integer, normalize to new dict form.
        if isinstance(value, int):
            value = {"page": value, "image": None, "blurb": ""}
        return super().to_python(value)

    def bulk_to_python(self, values):
        # Values is an iterable of raw list items (ints in old format, dicts in new).
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
    image_position = blocks.ChoiceBlock(
        choices=[("left", "Left"), ("right", "Right")],
        default="right",
        required=True,
    )

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

    class Meta:
        icon = "tick"
        label = "CTA"
        template = "pages/blocks/cta.html"


class HomeSections(blocks.StreamBlock):
    hero = HeroBlock()
    treatments = TreatmentsGridBlock()
    text_image = TextImageBlock()
    reviews_slider = ReviewsSliderBlock()
    cta = CTABlock()

    class Meta:
        label = "Homepage sections"
        icon = "list-ul"
