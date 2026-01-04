from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock


class TreatmentCarouselItem(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    subtitle = blocks.CharBlock(
        required=False,
        help_text="Optional price, tagline, or short descriptor",
    )

    image = ImageChooserBlock(required=False)
    video = DocumentChooserBlock(
        required=False,
        help_text="Optional MP4/WebM video. If set, video is used instead of image.",
    )

    link = blocks.URLBlock(required=False, help_text="Optional link / booking URL")

    class Meta:
        icon = "image"
        label = "Carousel item"
        help_text = "One card in the treatment carousel"


class TreatmentCarouselBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    items = blocks.ListBlock(TreatmentCarouselItem(), min_num=1)

    class Meta:
        icon = "placeholder"
        label = "Treatment carousel"
        template = "blocks/treatment_carousel.html"
