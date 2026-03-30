from wagtail import hooks
from django.utils.html import format_html
from django.templatetags.static import static

from .admin_dashboard import SkinmenuAnalyticsPanel, SkinmenuQuickLinksPanel

@hooks.register("insert_global_admin_js")
def media_picker_admin_js():
    return format_html(
        '<script src="{}"></script><script src="{}"></script>',
        static("js/media-position-picker.js"),
        static("js/wagtail-editor.js"),
    )

@hooks.register("insert_global_admin_css")
def media_picker_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}"><link rel="stylesheet" href="{}">',
        static("css/media-position-picker.css"),
        static("css/wagtail-admin.css"),
    )


@hooks.register("construct_homepage_panels")
def skinmenu_homepage_panels(request, panels):
    panels.insert(0, SkinmenuAnalyticsPanel())
    panels.insert(0, SkinmenuQuickLinksPanel())
