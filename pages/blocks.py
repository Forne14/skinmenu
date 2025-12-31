from wagtail import blocks
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
        help_text="Short, confident headline. Aim for one line on desktop."
    )
    subheadline = blocks.TextBlock(
        required=False,
        max_length=240,
        help_text="One short paragraph max. Keep it clean and editorial."
    )
    primary_cta = LinkBlock(required=False)
    secondary_cta = LinkBlock(required=False)
    image = ImageChooserBlock(required=False, help_text="Optional. Avoid needles; prefer skin/clinic/editorial.")

    class Meta:
        icon = "placeholder"
        label = "Hero"


class TextImageBlock(blocks.StructBlock):
    eyebrow = blocks.CharBlock(required=False, max_length=40, help_text="Optional small label above the heading.")
    heading = blocks.CharBlock(required=True, max_length=80)
    body = blocks.RichTextBlock(
        required=True,
        features=["bold", "italic", "link"],
        help_text="Keep paragraphs short. No long walls of copy."
    )
    image = ImageChooserBlock(required=False)
    image_position = blocks.ChoiceBlock(
        choices=[("left", "Left"), ("right", "Right")],
        default="right",
        required=True
    )

    class Meta:
        icon = "doc-full"
        label = "Text + Image"


class ReviewBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True, max_length=240)
    author = blocks.CharBlock(required=True, max_length=60)
    source = blocks.CharBlock(required=False, max_length=40, default="Google")

    class Meta:
        icon = "openquote"
        label = "Review"


class ReviewsSliderBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=60, default="Reviews")
    reviews = blocks.ListBlock(ReviewBlock(), min_num=1, max_num=12)

    class Meta:
        icon = "form"
        label = "Reviews Slider"


class CTABlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=True, max_length=80)
    body = blocks.TextBlock(required=False, max_length=240)
    primary_cta = LinkBlock(required=True)
    secondary_cta = LinkBlock(required=False)

    class Meta:
        icon = "tick"
        label = "Call to action"


class HomeSections(blocks.StreamBlock):
    hero = HeroBlock()
    text_image = TextImageBlock()
    reviews_slider = ReviewsSliderBlock()
    cta = CTABlock()

    class Meta:
        label = "Homepage sections"
        icon = "list-ul"
