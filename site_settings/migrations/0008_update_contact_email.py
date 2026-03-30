from django.db import migrations


OLD_EMAIL = "hello@skinmenu.co.uk"
NEW_EMAIL = "contact@skin-menu.co.uk"


def update_contact_email(apps, schema_editor):
    GlobalSiteSettings = apps.get_model("site_settings", "GlobalSiteSettings")
    GlobalSiteSettings.objects.filter(email=OLD_EMAIL).update(email=NEW_EMAIL)


def revert_contact_email(apps, schema_editor):
    GlobalSiteSettings = apps.get_model("site_settings", "GlobalSiteSettings")
    GlobalSiteSettings.objects.filter(email=NEW_EMAIL).update(email=OLD_EMAIL)


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0007_brandappearancesettings_footer_logo_variant_and_more"),
    ]

    operations = [
        migrations.RunPython(update_contact_email, revert_contact_email),
    ]
