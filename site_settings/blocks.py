from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.blocks import PageChooserBlock


class NavLinkBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=True, max_length=40)
    page = PageChooserBlock(required=False, help_text="Prefer selecting a page.")
    url = blocks.URLBlock(required=False, help_text="Use only if linking off-site.")
    open_in_new_tab = blocks.BooleanBlock(required=False, default=False)

    class Meta:
        icon = "link"
        label = "Navigation link"

    def clean(self, value):
        value = super().clean(value)
        if not value.get("page") and not value.get("url"):
            raise blocks.ValidationError("Select a page or provide a URL.")
        return value
