from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("pages", "0013_alter_aboutpage_sections_alter_homepage_sections_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="menusectionpage",
            name="category",
            field=models.ForeignKey(
                blank=True,
                help_text="Link this menu section to a treatment category.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="menu_pages",
                to="catalog.treatmentcategory",
            ),
        ),
        migrations.AddField(
            model_name="treatmentpage",
            name="treatment",
            field=models.ForeignKey(
                blank=True,
                help_text="Link this page to a normalized treatment record.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="detail_pages",
                to="catalog.treatment",
            ),
        ),
    ]
