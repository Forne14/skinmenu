from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Page, Site


@dataclass(frozen=True)
class SeedPage:
    title: str
    slug: str


class Command(BaseCommand):
    help = "Bootstrap local dev DB: superuser, site root, essential pages, and Wagtail settings."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="dev@skinmenu.local")
        parser.add_argument("--password", default="devpassword123")
        parser.add_argument("--domain", default="localhost")
        parser.add_argument("--port", default=8000, type=int)

    @transaction.atomic
    def handle(self, *args, **opts):
        email = opts["email"]
        password = opts["password"]
        domain = opts["domain"]
        port = opts["port"]

        self._ensure_superuser(email=email, password=password)

        root = Page.get_first_root_node()
        home = self._ensure_homepage(root)

        site = self._ensure_default_site(domain=domain, port=port, root_page=home)

        # Pages (structure derived from revamp spreadsheet)
        menu = self._ensure_standard_child(home, SeedPage("The Menu", "menu"))
        about = self._ensure_standard_child(home, SeedPage("About", "about"))
        contact = self._ensure_standard_child(home, SeedPage("Contact", "contact"))

        # Optional placeholder (handy if spreadsheet expects it later)
        blog = self._ensure_standard_child(home, SeedPage("Blog", "blog"))

        # Menu categories (placeholders)
        categories = [
            SeedPage("Lasers", "lasers"),
            SeedPage("Filler", "filler"),
            SeedPage("Botox", "botox"),
            SeedPage("Skin Boosters", "skin-boosters"),
            SeedPage("Biostimulators", "biostimulators"),
            SeedPage("Polynucleotides", "polynucleotides"),
            SeedPage("Hair", "hair"),
        ]

        category_pages: list[Page] = []
        category_by_slug: dict[str, Page] = {}
        for c in categories:
            p = self._ensure_standard_child(menu, c)
            category_pages.append(p)
            category_by_slug[c.slug] = p

        # Lasers sub-items (spreadsheet implies deeper IA under Lasers)
        lasers = category_by_slug.get("lasers")
        if lasers:
            laser_items = [
                SeedPage("PicoGenesis", "picogenesis"),
                SeedPage("PicoGenesis FX", "picogenesis-fx"),
                SeedPage("Laser Genesis", "laser-genesis"),
                SeedPage("Lipo-Laser", "lipo-laser"),
                SeedPage("PicoGlow", "picoglow"),
                SeedPage("Fractional CO2", "fractional-co2"),
                SeedPage("Laser Hair Removal", "laser-hair-removal"),
            ]
            for item in laser_items:
                self._ensure_standard_child(lasers, item)

        # Policies (placeholders)
        privacy = self._ensure_standard_child(home, SeedPage("Privacy Policy", "privacy"))
        cookies = self._ensure_standard_child(home, SeedPage("Cookies", "cookies"))
        terms = self._ensure_standard_child(home, SeedPage("Terms", "terms"))

        # Seed About / Contact with minimal structure (StreamField JSON; safe & editable)
        self._seed_standard_page_bodies(about=about, contact=contact)

        # Seed settings (safe defaults + nav links)
        self._seed_settings(
            site=site,
            home=home,
            menu=menu,
            about=about,
            contact=contact,
            privacy=privacy,
            cookies=cookies,
            terms=terms,
            category_pages=category_pages,
        )

        self.stdout.write(self.style.SUCCESS("bootstrap_dev complete."))
        self.stdout.write(self.style.WARNING(f"Superuser: {email} / {password}"))
        self.stdout.write("Log into /admin/ and tweak settings as needed.")

    def _ensure_superuser(self, email: str, password: str) -> None:
        """
        Creates or updates a superuser for local development.
        Wagtail uses Django auth; this ensures you can always log in after nuking db.sqlite3.
        """
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user and user.is_superuser:
            return

        if not user:
            user = User.objects.create_user(email=email, username=email)
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

    def _ensure_default_site(self, domain: str, port: int, root_page: Page) -> Site:
        """
        Ensures Wagtail has a default Site object pointing at our HomePage.
        Without this, routing / settings.for_site can behave unexpectedly.
        """
        site = Site.objects.filter(is_default_site=True).first()
        if site:
            changed = False
            if site.root_page_id != root_page.id:
                site.root_page = root_page
                changed = True
            if site.hostname != domain:
                site.hostname = domain
                changed = True
            if site.port != port:
                site.port = port
                changed = True
            if changed:
                site.save()
            return site

        return Site.objects.create(
            hostname=domain,
            port=port,
            site_name="SKINMENU (Dev)",
            root_page=root_page,
            is_default_site=True,
        )

    def _ensure_homepage(self, root: Page) -> Page:
        """
        Ensures a HomePage exists under the root.
        Uses pages.models.HomePage so editors can manage sections via StreamField.
        """
        from pages.models import HomePage

        existing = root.get_children().type(HomePage).first()
        if existing:
            return existing.specific

        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
        home.save_revision().publish()
        return home

    def _ensure_standard_child(self, parent: Page, p: SeedPage) -> Page:
        """
        Idempotently creates StandardPage children, so re-running bootstrap_dev is safe.
        """
        from pages.models import StandardPage

        existing = parent.get_children().filter(slug=p.slug).first()
        if existing:
            return existing.specific

        page = StandardPage(title=p.title, slug=p.slug)
        parent.add_child(instance=page)
        page.save_revision().publish()
        return page

    def _seed_standard_page_bodies(self, about: Page, contact: Page) -> None:
        """
        Seeds minimal content into About/Contact if empty.
        Uses StreamField JSON (list of {"type": "...", "value": ...} dicts).
        """
        from pages.models import StandardPage

        if isinstance(about.specific, StandardPage) and not about.specific.body:
            about.specific.body = [
                {"type": "heading", "value": "SKIN MENU"},
                {
                    "type": "rich_text",
                    "value": "<p>A premium, minimal approach to skin health — curated like a menu.</p>",
                },
                {"type": "heading", "value": "OUR VALUES"},
                {
                    "type": "rich_text",
                    "value": "<ul><li>Subtle, natural outcomes</li><li>Evidence-led treatments</li><li>Quiet luxury care</li></ul>",
                },
                {"type": "heading", "value": "OUR FOUNDER"},
                {"type": "rich_text", "value": "<p>Add founder bio and credentials here.</p>"},
                {"type": "heading", "value": "YOUR TEAM (FUTURE)"},
                {"type": "rich_text", "value": "<p>Optional: introduce additional clinicians as the team grows.</p>"},
            ]
            about.specific.save_revision().publish()

        if isinstance(contact.specific, StandardPage) and not contact.specific.body:
            contact.specific.body = [
                {"type": "heading", "value": "ENQUIRE"},
                {
                    "type": "rich_text",
                    "value": "<p>Email us at <a href='mailto:hello@skinmenu.co.uk'>hello@skinmenu.co.uk</a>.</p>",
                },
                {"type": "heading", "value": "VISIT"},
                {"type": "rich_text", "value": "<p>Add your clinic address here, plus a Google Maps link.</p>"},
            ]
            contact.specific.save_revision().publish()

    def _seed_settings(
        self,
        site: Site,
        home: Page,
        menu: Page,
        about: Page,
        contact: Page,
        privacy: Page,
        cookies: Page,
        terms: Page,
        category_pages: list[Page],
    ) -> None:
        """
        Seeds Wagtail "Settings" models with sensible defaults.

        Important detail:
        - StreamField JSON must be serializable.
        - PageChooserBlock stores *page IDs* (ints), not Page objects.
        """
        from site_settings.models import (
            AnalyticsSettings,
            BrandAppearanceSettings,
            GlobalSiteSettings,
            NavigationSettings,
        )

        # Ensure settings rows exist
        gs = GlobalSiteSettings.for_site(site)
        nav = NavigationSettings.for_site(site)
        AnalyticsSettings.for_site(site)
        BrandAppearanceSettings.for_site(site)

        # GlobalSiteSettings (client preference: no phone/hours in UI; keep fields blank)
        self._set_if_exists(gs, "clinic_name", "SKINMENU")
        self._set_if_exists(gs, "email", "hello@skinmenu.co.uk")
        self._set_if_exists(gs, "address", "London, United Kingdom")
        self._set_if_exists(gs, "opening_hours", "")
        self._set_if_exists(gs, "phone", "")
        gs.save()

        def link(
            label: str,
            page: Optional[Page] = None,
            url: Optional[str] = None,
            new_tab: bool = False,
        ):
            """
            Builds a NavLinkBlock JSON value.
            Exactly one of page or url should be provided (block clean() enforces this).
            """
            data = {"label": label, "open_in_new_tab": new_tab}
            if page is not None:
                data["page"] = page.id
            if url is not None:
                data["url"] = url
            return data

        self._set_if_exists(nav, "menu_label", "The Menu")

        primary = [
            {"type": "link", "value": link("The Menu", page=menu)},
            {"type": "link", "value": link("About", page=about)},
            {"type": "link", "value": link("Contact", page=contact)},
        ]
        self._set_if_exists(nav, "primary_links", primary)

        menu_links = [{"type": "link", "value": link(p.title, page=p)} for p in category_pages]
        self._set_if_exists(nav, "menu_links", menu_links)

        header_cta = [{"type": "link", "value": link("Book a consultation", page=contact)}]
        self._set_if_exists(nav, "header_cta", header_cta)

        footer_links = [
            {"type": "link", "value": link("The Menu", page=menu)},
            {"type": "link", "value": link("About", page=about)},
            {"type": "link", "value": link("Contact", page=contact)},
            {"type": "link", "value": link("Privacy", page=privacy)},
            {"type": "link", "value": link("Cookies", page=cookies)},
            {"type": "link", "value": link("Terms", page=terms)},
        ]
        self._set_if_exists(nav, "footer_links", footer_links)

        nav.save()

    def _set_if_exists(self, obj, field: str, value) -> None:
        """
        Defensive helper: lets bootstrap_dev run even if some fields change names later.
        """
        if hasattr(obj, field):
            setattr(obj, field, value)
