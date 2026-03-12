from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from integrations.admin_views import outbound_events_view


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        path("integrations/outbound-events/", outbound_events_view, name="integrations_outbound_events"),
    ]


@hooks.register("register_admin_menu_item")
def register_outbound_events_menu_item():
    return MenuItem(
        "Outbound Events",
        reverse("integrations_outbound_events"),
        icon_name="warning",
        order=950,
    )
