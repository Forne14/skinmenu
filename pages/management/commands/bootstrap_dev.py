from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Page, Site


@dataclass(frozen=True)
class SeedPage:
    title: str
    slug: str


BASE_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = Path("/mnt/data")  # works in ChatGPT sandbox; local dev falls back below.

CSV_CONTACT = [
    DATA_DIR / "WEBSITE REVAMP - Contact Us(1).csv",
    BASE_DIR / "WEBSITE REVAMP - Contact Us(1).csv",
    BASE_DIR / "data" / "WEBSITE REVAMP - Contact Us(1).csv",
]
CSV_ABOUT = [
    DATA_DIR / "WEBSITE REVAMP - About Us(1).csv",
    BASE_DIR / "WEBSITE REVAMP - About Us(1).csv",
    BASE_DIR / "data" / "WEBSITE REVAMP - About Us(1).csv",
]
CSV_TREATMENTS = [
    DATA_DIR / "WEBSITE REVAMP - Treatments(1).csv",
    BASE_DIR / "WEBSITE REVAMP - Treatments(1).csv",
    BASE_DIR / "data" / "WEBSITE REVAMP - Treatments(1).csv",
]


def slugify_basic(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "item"


def first_existing(paths: list[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


def read_csv_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


class Command(BaseCommand):
    help = "Bootstrap local dev DB: superuser, site root, essential pages, and Wagtail settings."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="dev@skinmenu.local")
        parser.add_argument("--password", default="devpassword123")
        parser.add_argument("--domain", default="localhost")
        parser.add_argument("--port", default=8000, type=int)
        parser.add_argument(
            "--force-replace-wrong-types",
            action="store_true",
            default=False,  # IMPORTANT: safe by default
            help="If a slug exists but is the wrong Page type, delete + recreate (DEV ONLY). Default: False.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        email = opts["email"]
        password = opts["password"]
        domain = opts["domain"]
        port = opts["port"]
        force_replace = opts["force_replace_wrong_types"]

        self._ensure_superuser(email=email, password=password)

        root = Page.get_first_root_node()
        home = self._ensure_homepage(root)

        site = self._ensure_default_site(domain=domain, port=port, root_page=home)

        # Import models inside handle (after Django setup)
        from pages.models import (
            AboutTeamMember,
            AboutPage,
            BlogIndexPage,
            ContactPage,
            MenuSectionPage,
            StandardPage,
            TreatmentPage,
            TreatmentsIndexPage,
        )

        # Ensure core pages with correct types
        menu = self._ensure_typed_child(
            home, TreatmentsIndexPage, SeedPage("The Menu", "menu"), force_replace=force_replace
        )
        about = self._ensure_typed_child(
            home, AboutPage, SeedPage("About", "about"), force_replace=force_replace
        )
        contact = self._ensure_typed_child(
            home, ContactPage, SeedPage("Contact", "contact"), force_replace=force_replace
        )
        blog = self._ensure_typed_child(
            home, BlogIndexPage, SeedPage("Blog", "blog"), force_replace=force_replace
        )

        # Policies as StandardPage
        privacy = self._ensure_typed_child(home, StandardPage, SeedPage("Privacy Policy", "privacy"), force_replace=False)
        cookies = self._ensure_typed_child(home, StandardPage, SeedPage("Cookies", "cookies"), force_replace=False)
        terms = self._ensure_typed_child(home, StandardPage, SeedPage("Terms", "terms"), force_replace=False)

        # Seed content (only if empty)
        self._seed_about_from_csv(about=about, AboutTeamMember=AboutTeamMember)
        self._seed_contact_basics(contact=contact)
        self._seed_menu_from_csv(menu=menu, MenuSectionPage=MenuSectionPage, TreatmentPage=TreatmentPage)

        # Repair homepage references if pages were replaced (or if DB has stale refs)
        self._repair_homepage_sections(home=home, menu=menu)

        # Seed settings + nav links
        self._seed_settings(
            site=site,
            home=home,
            menu=menu,
            about=about,
            contact=contact,
            blog=blog,
            privacy=privacy,
            cookies=cookies,
            terms=terms,
        )

        self.stdout.write(self.style.SUCCESS("bootstrap_dev complete."))
        self.stdout.write(self.style.WARNING(f"Superuser: {email} / {password}"))
        self.stdout.write("Log into /admin/ and tweak settings as needed.")

    # ---------------------------
    # Core ensure helpers
    # ---------------------------

    def _ensure_superuser(self, email: str, password: str) -> None:
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
        from pages.models import HomePage

        existing = root.get_children().type(HomePage).first()
        if existing:
            return existing.specific

        home = HomePage(title="Home", slug="home")
        root.add_child(instance=home)
        home.save_revision().publish()
        return home

    def _ensure_typed_child(self, parent: Page, model_cls, p: SeedPage, force_replace: bool) -> Page:
        """
        Ensures a specific child slug exists under parent with the correct page model type.
        If the slug exists but wrong type, optionally delete and recreate (DEV ONLY).
        """
        existing = parent.get_children().filter(slug=p.slug).first()
        if existing:
            specific = existing.specific
            if isinstance(specific, model_cls):
                return specific

            if force_replace:
                existing.delete()
            else:
                return specific  # best-effort fallback

        page = model_cls(title=p.title, slug=p.slug)
        parent.add_child(instance=page)
        page.save_revision().publish()
        return page.specific

    # ---------------------------
    # Homepage repair (critical futureproofing)
    # ---------------------------

    def _repair_homepage_sections(self, home: Page, menu: Page) -> None:
        """
        Repairs stale page references inside HomePage.sections after dev reseeds.
        - Ensures treatments/featured_menu blocks have valid CTA page
        - Removes tiles that point at missing pages
        - If a treatments block ends up too empty, repopulates from /menu children
        """
        from wagtail.models import Page as WagtailPage

        if not hasattr(home, "sections"):
            return

        # Build a stable pool for homepage tiles (first-level under /menu)
        menu_children = list(menu.get_children().live().public())
        menu_child_ids = [p.id for p in menu_children]

        def page_exists(page_id: int) -> bool:
            return WagtailPage.objects.filter(id=page_id).exists()

        changed = False
        data = list(getattr(home.sections, "stream_data", []) or [])

        if not data:
            # If empty homepage, don't invent editorial copy, but do give it a working scaffold.
            # Editors can refine in Wagtail, but site won't be broken.
            items = [{"page": pid, "image": None, "blurb": ""} for pid in menu_child_ids[:7]]
            if len(items) >= 3:
                data = [
                    {"type": "hero", "value": {"headline": "Your best skin, on the menu", "subheadline": "", "primary_cta": {"label": "Book", "url": "/contact/"}, "cta_position": "bottom_left", "hero_images": []}},
                    {"type": "treatments", "value": {"heading": "Treatments", "intro": "", "items": items, "cta_label": "See full menu", "cta_page": menu.id}},
                ]
                changed = True

        # Repair existing
        for block in data:
            btype = block.get("type")
            val = block.get("value") or {}

            # Ensure CTA page points somewhere real
            if btype in {"treatments", "featured_menu"}:
                cta_page = val.get("cta_page")
                if isinstance(cta_page, int) and not page_exists(cta_page):
                    val["cta_page"] = menu.id
                    changed = True

            # Legacy featured_menu: featured_pages is a list of ints (page ids)
            if btype == "featured_menu":
                fp = val.get("featured_pages") or []
                if isinstance(fp, list):
                    new_fp = [pid for pid in fp if isinstance(pid, int) and page_exists(pid)]
                    if new_fp != fp:
                        val["featured_pages"] = new_fp
                        changed = True
                block["value"] = val

            # New treatments block: items list contains dicts with "page" ids
            if btype == "treatments":
                items = val.get("items") or []
                if isinstance(items, list):
                    cleaned = []
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        pid = it.get("page")
                        if isinstance(pid, int) and page_exists(pid):
                            cleaned.append(it)
                    if cleaned != items:
                        val["items"] = cleaned
                        changed = True

                    # Ensure minimum viable tiles; repopulate from /menu if needed
                    if len(val.get("items") or []) < 3 and menu_child_ids:
                        val["items"] = [{"page": pid, "image": None, "blurb": ""} for pid in menu_child_ids[:7]]
                        changed = True

                block["value"] = val

        if changed:
            home.sections = data
            home.save_revision().publish()

    # ---------------------------
    # About seeding
    # ---------------------------

    def _seed_about_from_csv(self, about, AboutTeamMember) -> None:
        if about.sections and len(about.sections):
            return

        about_csv_path = first_existing(CSV_ABOUT)
        rows = read_csv_rows(about_csv_path) if about_csv_path else []

        def find(keyword: str) -> str:
            k = keyword.lower()
            for r in rows:
                feat = (r.get("Feature") or r.get("Feature ") or "").lower()
                change = (r.get("Change") or "").strip()
                if k in feat and change:
                    return change
            return ""

        who = find("who") or "A curated, clinician-led approach to modern skin health."
        founder = find("founder") or "Founded with a belief in subtle, evidence-led outcomes."
        values_raw = find("values")

        value_items = []
        if values_raw:
            for line in values_raw.split("\n"):
                line = line.strip()
                if line:
                    value_items.append({"title": line[:60], "text": line})
        else:
            value_items = [
                {"title": "Subtle results", "text": "Enhancing, never overcorrecting."},
                {"title": "Evidence-led", "text": "Treatments grounded in medical science."},
                {"title": "Clinician-first", "text": "Every plan begins with consultation."},
            ]

        about.sections = [
            {
                "type": "hero",
                "value": {
                    "headline": "About SKINMENU",
                    "subheadline": "A modern, clinician-led skin destination.",
                    "cta_position": "bottom_left",
                    "hero_images": [],
                },
            },
            {
                "type": "who",
                "value": {
                    "eyebrow": "About",
                    "heading": "Who we are",
                    "body": f"<p>{who}</p>",
                    "buttons": [],
                },
            },
            {
                "type": "values",
                "value": {
                    "eyebrow": "Principles",
                    "heading": "Our values",
                    "values": value_items,
                },
            },
            {
                "type": "founder",
                "value": {
                    "eyebrow": "Founder",
                    "heading": "Our founder",
                    "body": f"<p>{founder}</p>",
                    "buttons": [],
                },
            },
        ]

        about.save_revision().publish()

        if about.team_members.count() == 0:
            AboutTeamMember.objects.create(
                page=about,
                name="Dr Tego Kirnon-Jackman",
                role="Founder / Medical Director",
                experience="Aesthetic medicine",
                bio=founder,
            )

    # ---------------------------
    # Contact seeding
    # ---------------------------

    def _seed_contact_basics(self, contact) -> None:
        changed = False

        if not getattr(contact, "intro", ""):
            contact.intro = "<p>Email us and we’ll respond with consultation availability.</p>"
            changed = True

        if not getattr(contact, "thank_you_text", ""):
            contact.thank_you_text = "<p>Thank you — we’ve received your message and will respond shortly.</p>"
            changed = True

        if not getattr(contact, "to_address", ""):
            contact.to_address = "hello@skinmenu.co.uk"
            changed = True
        if not getattr(contact, "from_address", ""):
            contact.from_address = "no-reply@skinmenu.local"
            changed = True
        if not getattr(contact, "subject", ""):
            contact.subject = "New enquiry — SKINMENU"
            changed = True

        if contact.form_fields.count() == 0:
            from pages.models import ContactPageFormField

            ContactPageFormField.objects.create(
                page=contact,
                label="Name",
                field_type="singleline",
                required=True,
                sort_order=0,
            )
            ContactPageFormField.objects.create(
                page=contact,
                label="Email",
                field_type="email",
                required=True,
                sort_order=1,
            )
            ContactPageFormField.objects.create(
                page=contact,
                label="Message",
                field_type="multiline",
                required=True,
                sort_order=2,
            )

        if changed:
            contact.save_revision().publish()

    # ---------------------------
    # Menu / treatments seeding
    # ---------------------------

    def _seed_menu_from_csv(self, menu, MenuSectionPage, TreatmentPage) -> None:
        path = first_existing(CSV_TREATMENTS)
        rows = read_csv_rows(path) if path else []

        main_sections: dict[str, list[str]] = {}
        for r in rows:
            feat = (r.get("Feature") or r.get("Feature ") or "").strip()
            change = (r.get("Change") or "").strip()
            if not feat:
                continue

            if feat.lower() in ["lasers", "filler", "botox", "skin-boosters", "biostimulators", "polynucleotides", "hair"]:
                subitems = [s.strip() for s in change.split("\n") if s.strip()] if change else []
                main_sections[feat] = subitems

        if not main_sections:
            main_sections = {
                "Lasers": ["PicoGenesis", "PicoGenesis FX", "Laser Genesis", "Lipo-Laser", "PicoGlow", "Fractional CO2", "Laser Hair Removal"],
                "Filler": [],
                "Botox": [],
                "Skin Boosters": [],
                "Biostimulators": [],
                "Polynucleotides": [],
                "Hair": [],
            }

        if hasattr(menu, "intro") and not (menu.intro or "").strip():
            menu.intro = "<p>Explore the menu by category. Each treatment page includes key facts, what to expect, and FAQs.</p>"
            menu.save_revision().publish()

        for section_title, subitems in main_sections.items():
            section_slug = slugify_basic(section_title)
            section_page = menu.get_children().filter(slug=section_slug).first()
            if section_page:
                section_specific = section_page.specific
                if not isinstance(section_specific, MenuSectionPage):
                    section_page.delete()
                    section_specific = None
            else:
                section_specific = None

            if section_specific is None:
                section_specific = MenuSectionPage(title=section_title, slug=section_slug)
                menu.add_child(instance=section_specific)
                section_specific.save_revision().publish()

            if not (getattr(section_specific, "intro", "") or "").strip():
                section_specific.intro = "<p>Add a short editorial introduction for this section.</p>"
                section_specific.save_revision().publish()

            for name in subitems:
                if name.lower() in {"overview", "areas treated", "skinboosters offered", "hair treatments offered", "sub-sections"}:
                    continue

                t_slug = slugify_basic(name)
                existing = section_specific.get_children().filter(slug=t_slug).first()
                if existing:
                    tp = existing.specific
                    if not isinstance(tp, TreatmentPage):
                        existing.delete()
                        tp = None
                else:
                    tp = None

                if tp is None:
                    tp = TreatmentPage(title=name, slug=t_slug)
                    section_specific.add_child(instance=tp)
                    tp.save_revision().publish()

                changed = False
                if hasattr(tp, "summary") and not (tp.summary or "").strip():
                    tp.summary = "Add a one-paragraph summary explaining outcomes, suitability, and approach."
                    changed = True

                if not tp.sections:
                    tp.sections = [
                        {
                            "type": "key_facts",
                            "value": {
                                "eyebrow": "",
                                "heading": "Key facts",
                                "facts": [
                                    {"label": "Duration", "value": "TBC"},
                                    {"label": "Downtime", "value": "TBC"},
                                    {"label": "From", "value": "TBC"},
                                ],
                            },
                        },
                        {
                            "type": "steps",
                            "value": {
                                "eyebrow": "",
                                "heading": "What to expect",
                                "steps": [
                                    {"title": "Consultation", "text": "<p>We discuss goals, suitability, and a personalised plan.</p>"},
                                    {"title": "Treatment", "text": "<p>The procedure is performed with a focus on comfort and precision.</p>"},
                                    {"title": "Aftercare", "text": "<p>Clear guidance and follow-up recommendations are provided.</p>"},
                                ],
                            },
                        },
                        {
                            "type": "faq",
                            "value": {
                                "eyebrow": "",
                                "heading": "Frequently asked questions",
                                "items": [
                                    {"question": "Is this treatment suitable for me?", "answer": "<p>Suitability is confirmed during consultation.</p>"},
                                    {"question": "When will I see results?", "answer": "<p>Timelines vary—your clinician will advise based on the treatment.</p>"},
                                ],
                            },
                        },
                        {
                            "type": "cta",
                            "value": {
                                "heading": "Book a consultation",
                                "body": "Discuss the right option for your skin with a clinician-led consultation.",
                                "primary_cta": {"label": "Enquire", "url": "/contact/"},
                                "secondary_cta": {"label": "Explore the menu", "url": "/menu/"},
                            },
                        },
                    ]
                    changed = True

                if changed:
                    tp.save_revision().publish()

    # ---------------------------
    # Settings seeding
    # ---------------------------

    def _seed_settings(
        self,
        site: Site,
        home: Page,
        menu: Page,
        about: Page,
        contact: Page,
        blog: Page,
        privacy: Page,
        cookies: Page,
        terms: Page,
    ) -> None:
        from site_settings.models import (
            AnalyticsSettings,
            BrandAppearanceSettings,
            GlobalSiteSettings,
            NavigationSettings,
        )

        gs = GlobalSiteSettings.for_site(site)
        nav = NavigationSettings.for_site(site)
        AnalyticsSettings.for_site(site)
        BrandAppearanceSettings.for_site(site)

        self._set_if_empty(gs, "clinic_name", "SKINMENU")
        self._set_if_empty(gs, "email", "hello@skinmenu.co.uk")
        self._set_if_empty(gs, "address", "London, United Kingdom")
        gs.save()

        def nav_link(label: str, page: Optional[Page] = None, url: Optional[str] = None, new_tab: bool = False):
            data = {"label": label, "open_in_new_tab": new_tab}
            if page is not None:
                data["page"] = page.id
            if url is not None:
                data["url"] = url
            return data

        # Always ensure core nav links are valid (ids can change in dev)
        nav.primary_links = [
            {"type": "link", "value": nav_link("The Menu", page=menu)},
            {"type": "link", "value": nav_link("About", page=about)},
            {"type": "link", "value": nav_link("Blog", page=blog)},
            {"type": "link", "value": nav_link("Contact", page=contact)},
        ]

        children = menu.get_children().live().public()
        nav.menu_links = [{"type": "link", "value": nav_link(c.title, page=c)} for c in children]

        nav.header_cta = [{"type": "link", "value": nav_link("Book a consultation", page=contact)}]

        nav.footer_links = [
            {"type": "link", "value": nav_link("The Menu", page=menu)},
            {"type": "link", "value": nav_link("About", page=about)},
            {"type": "link", "value": nav_link("Blog", page=blog)},
            {"type": "link", "value": nav_link("Contact", page=contact)},
            {"type": "link", "value": nav_link("Privacy", page=privacy)},
            {"type": "link", "value": nav_link("Cookies", page=cookies)},
            {"type": "link", "value": nav_link("Terms", page=terms)},
        ]

        nav.save()

    def _set_if_empty(self, obj, field: str, value) -> None:
        if hasattr(obj, field):
            current = getattr(obj, field)
            if current is None or (isinstance(current, str) and not current.strip()):
                setattr(obj, field, value)
