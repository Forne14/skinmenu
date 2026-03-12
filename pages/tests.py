from django.core.exceptions import ValidationError
from django.core.management import call_command
from io import StringIO

from catalog.models import Treatment, TreatmentOption
from pages.models import HomePage, TreatmentsIndexPage, MenuSectionPage, TreatmentPage, ContactPage
from pages.blocks import BlogImageBlock
from site_settings.models import GlobalSiteSettings

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase


class HomeSetUpTests(WagtailPageTestCase):
    """
    Tests for basic page structure setup and HomePage creation.
    """

    def test_root_create(self):
        root_page = Page.objects.get(pk=1)
        self.assertIsNotNone(root_page)

    def test_homepage_create(self):
        root_page = Page.objects.get(pk=1)
        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)
        self.assertTrue(HomePage.objects.filter(title="Home").exists())


class HomeTests(WagtailPageTestCase):
    """
    Tests for homepage functionality and rendering.
    """

    def setUp(self):
        """
        Create a homepage instance for testing.
        """
        root_page = Page.get_first_root_node()
        Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.homepage = HomePage(title="Home")
        root_page.add_child(instance=self.homepage)

    def test_homepage_is_renderable(self):
        self.assertPageIsRenderable(self.homepage)

    def test_homepage_template_used(self):
        response = self.client.get(self.homepage.url)
        self.assertTemplateUsed(response, "pages/home_page.html")


class PageLinkValidationTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.home = HomePage(title="Home")
        root_page.add_child(instance=self.home)
        self.menu_index = self.home.add_child(instance=TreatmentsIndexPage(title="Menu"))

        self.treatment = Treatment.objects.create(name="Laser", slug="laser")
        self.option = TreatmentOption.objects.create(treatment=self.treatment, name="Laser Option")

    def test_menu_section_requires_treatment(self):
        with self.assertRaises(ValidationError):
            self.menu_index.add_child(instance=MenuSectionPage(title="Section"))

    def test_treatment_page_requires_option(self):
        section_invalid = self.menu_index.add_child(
            instance=MenuSectionPage(title="Section Linked Invalid", treatment=self.treatment)
        )
        with self.assertRaises(ValidationError):
            section_invalid.add_child(instance=TreatmentPage(title="Detail"))

        section_valid = self.menu_index.add_child(
            instance=MenuSectionPage(title="Section Linked Valid", treatment=self.treatment)
        )
        detail = section_valid.add_child(instance=TreatmentPage(title="Detail Linked", option=self.option))
        detail.full_clean()


class BlogImageBlockValidationTests(WagtailPageTestCase):
    def test_accepts_empty_media(self):
        block = BlogImageBlock()
        cleaned = block.clean({"image": None, "media": {"image": None, "video": None}, "caption": ""})
        self.assertIsNotNone(cleaned)


class ContactPageMailtoTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        self.site = Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.home = HomePage(title="Home")
        root_page.add_child(instance=self.home)
        self.contact_page = self.home.add_child(instance=ContactPage(title="Contact"))

    def test_renders_mailto_button_using_admin_email(self):
        gs = GlobalSiteSettings.for_site(self.site)
        gs.email = "drtego@example.com"
        gs.save()

        response = self.client.get(self.contact_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Mail")
        self.assertContains(response, 'href="mailto:drtego@example.com"', html=False)
        self.assertNotContains(response, "Email Dr Tego")
        self.assertNotContains(response, "Share a little context and we’ll respond with next steps.")

    def test_hides_button_when_admin_email_missing(self):
        gs = GlobalSiteSettings.for_site(self.site)
        gs.email = ""
        gs.save()

        response = self.client.get(self.contact_page.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Open Mail")
        self.assertNotContains(response, 'href="mailto:', html=False)


class LegacyContentCommandsTests(WagtailPageTestCase):
    def setUp(self):
        root_page = Page.get_first_root_node()
        self.site = Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.home = HomePage(title="Home")
        root_page.add_child(instance=self.home)

    def test_audit_legacy_content_reports_issues(self):
        self.home.sections = [
            {
                "type": "featured_menu",
                "value": {"heading": "", "intro": "", "featured_pages": [], "cta_label": "", "cta_page": None},
            }
        ]
        self.home.save(update_fields=["sections"])

        out = StringIO()
        call_command("audit_legacy_content", stdout=out)
        text = out.getvalue()
        self.assertIn("legacy_blocks: 1", text)
        self.assertIn("issues_total:", text)

    def test_cleanup_legacy_content_dry_run_does_not_persist(self):
        self.home.sections = [
            {
                "type": "featured_menu",
                "value": {"heading": "", "intro": "", "featured_pages": [], "cta_label": "", "cta_page": None},
            }
        ]
        self.home.save(update_fields=["sections"])

        call_command("cleanup_legacy_content")
        self.home.refresh_from_db()
        self.assertEqual(len(self.home.sections.raw_data), 1)

    def test_cleanup_legacy_content_apply_persists(self):
        self.home.sections = [
            {
                "type": "featured_menu",
                "value": {"heading": "", "intro": "", "featured_pages": [], "cta_label": "", "cta_page": None},
            }
        ]
        self.home.save(update_fields=["sections"])

        call_command("cleanup_legacy_content", "--apply")
        self.home.refresh_from_db()
        self.assertEqual(len(self.home.sections.raw_data), 0)
