from wagtail import hooks
from django.utils.html import format_html
from django.templatetags.static import static

@hooks.register("insert_global_admin_js")
def media_picker_admin_js():

    return format_html('<script src="{}"></script>', static("js/media_position_picker.js"))

@hooks.register("insert_global_admin_css")
def media_picker_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("css/media-position-picker.css"))

