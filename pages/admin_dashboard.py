from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from django.urls import NoReverseMatch, reverse

from wagtail.admin.ui.components import Component
from wagtail.models import Page

from site_settings.models import AnalyticsSettings

from pages.models import (
    AboutPage,
    BlogIndexPage,
    ContactPage,
    HomePage,
    TreatmentsIndexPage,
)


@dataclass
class QuickLink:
    label: str
    url: Optional[str]
    helper: Optional[str] = None


def _safe_reverse(view_name: str, args: Optional[list] = None) -> Optional[str]:
    try:
        return reverse(view_name, args=args or [])
    except NoReverseMatch:
        return None


def _first_page_edit_url(page_model) -> Optional[str]:
    page = Page.objects.type(page_model).live().first()
    if not page:
        return None
    return _safe_reverse("wagtailadmin_pages:edit", [page.id])


def build_quicklinks() -> List[QuickLink]:
    return [
        QuickLink("Homepage", _first_page_edit_url(HomePage), "Hero, modules, and highlights"),
        QuickLink("Menu index", _first_page_edit_url(TreatmentsIndexPage), "Menu overview + featured"),
        QuickLink("About page", _first_page_edit_url(AboutPage), "Team, story, and values"),
        QuickLink("Contact page", _first_page_edit_url(ContactPage), "Location + contact blocks"),
        QuickLink("Journal", _first_page_edit_url(BlogIndexPage), "Blog landing + posts"),
        QuickLink("Snippets", _safe_reverse("wagtailsnippets:index"), "Treatments, prices, media, facts"),
    ]


class SkinmenuQuickLinksPanel(Component):
    name = "skinmenu_quicklinks"
    template_name = "wagtailadmin/home/skinmenu_quicklinks.html"
    order = 120

    def get_context_data(self, parent_context):
        return {
            "quicklinks": build_quicklinks(),
        }


class SkinmenuAnalyticsPanel(Component):
    name = "skinmenu_analytics"
    template_name = "wagtailadmin/home/skinmenu_analytics.html"
    order = 130

    def get_context_data(self, parent_context):
        request = parent_context["request"]
        analytics_settings = AnalyticsSettings.for_request(request)

        return {
            "analytics_settings": analytics_settings,
            "ga4_connected": bool(analytics_settings.ga4_measurement_id),
            "meta_connected": bool(analytics_settings.meta_pixel_id),
        }
