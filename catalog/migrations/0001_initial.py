from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields
import wagtail.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("wagtaildocs", "0001_initial"),
        ("wagtailimages", "0001_initial"),
        ("wagtailcore", "0001_squashed_0016_change_page_url_path_to_text_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClinicLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=80)),
                ("postcode", models.CharField(blank=True, max_length=40)),
                ("country", models.CharField(blank=True, max_length=80)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("hours", models.TextField(blank=True)),
                ("map_url", models.URLField(blank=True)),
                ("map_embed_url", models.URLField(blank=True, max_length=2000)),
                ("timezone", models.CharField(blank=True, max_length=60)),
                ("is_primary", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Clinic location",
                "verbose_name_plural": "Clinic locations",
            },
        ),
        migrations.CreateModel(
            name="ContentBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "block_type",
                    models.CharField(
                        choices=[
                            ("hero", "Hero"),
                            ("rich_text", "Rich text"),
                            ("text_media", "Text + media"),
                            ("cta", "CTA"),
                            ("faq", "FAQ"),
                            ("steps", "Steps"),
                            ("reviews", "Reviews"),
                            ("products", "Products"),
                        ],
                        max_length=20,
                    ),
                ),
                ("eyebrow", models.CharField(blank=True, max_length=60)),
                ("heading", models.CharField(blank=True, max_length=120)),
                ("subheading", models.CharField(blank=True, max_length=120)),
                ("body", wagtail.fields.RichTextField(blank=True)),
                ("primary_cta_label", models.CharField(blank=True, max_length=60)),
                ("primary_cta_url", models.URLField(blank=True)),
                ("secondary_cta_label", models.CharField(blank=True, max_length=60)),
                ("secondary_cta_url", models.URLField(blank=True)),
                (
                    "media_position",
                    models.CharField(
                        choices=[("left", "Left"), ("right", "Right")],
                        default="right",
                        max_length=10,
                    ),
                ),
                ("loop", models.BooleanField(default=True)),
                (
                    "playback_rate",
                    models.CharField(
                        choices=[
                            ("0.75", "0.75x (slow)"),
                            ("1.0", "1.0x (normal)"),
                            ("1.25", "1.25x (fast)"),
                            ("1.5", "1.5x (fast)"),
                        ],
                        default="1.0",
                        max_length=8,
                    ),
                ),
                (
                    "media_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
                (
                    "media_video",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtaildocs.document",
                    ),
                ),
            ],
            options={
                "verbose_name": "Content block",
                "verbose_name_plural": "Content blocks",
            },
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote", models.TextField(max_length=420)),
                ("author", models.CharField(max_length=80)),
                ("source", models.CharField(blank=True, max_length=80)),
                ("link", models.URLField(blank=True)),
                ("rating", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to="catalog.cliniclocation",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "author"],
            },
        ),
        migrations.CreateModel(
            name="TeamMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("role", models.CharField(blank=True, max_length=120)),
                ("experience", models.CharField(blank=True, max_length=120)),
                ("bio", models.TextField(blank=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="team_members",
                        to="catalog.cliniclocation",
                    ),
                ),
                (
                    "photo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="TreatmentCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("description", wagtail.fields.RichTextField(blank=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "featured_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "name"],
                "verbose_name": "Treatment category",
                "verbose_name_plural": "Treatment categories",
            },
        ),
        migrations.CreateModel(
            name="Treatment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("summary", models.TextField(blank=True, max_length=300)),
                ("long_description", wagtail.fields.RichTextField(blank=True)),
                ("duration", models.CharField(blank=True, max_length=80)),
                ("downtime", models.CharField(blank=True, max_length=80)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treatments",
                        to="catalog.treatmentcategory",
                    ),
                ),
                (
                    "primary_location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treatments",
                        to="catalog.cliniclocation",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "name"],
                "verbose_name": "Treatment",
                "verbose_name_plural": "Treatments",
            },
        ),
        migrations.CreateModel(
            name="SocialProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(max_length=40)),
                ("url", models.URLField()),
                ("handle", models.CharField(blank=True, max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="social_profiles",
                        to="catalog.cliniclocation",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "platform"],
                "verbose_name": "Social profile",
                "verbose_name_plural": "Social profiles",
            },
        ),
        migrations.CreateModel(
            name="ContentBlockItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("title", models.CharField(blank=True, max_length=120)),
                ("body", wagtail.fields.RichTextField(blank=True)),
                ("label", models.CharField(blank=True, max_length=80)),
                ("value", models.CharField(blank=True, max_length=160)),
                ("url", models.URLField(blank=True)),
                ("price_text", models.CharField(blank=True, max_length=60)),
                ("cta_label", models.CharField(blank=True, max_length=60)),
                ("cta_url", models.URLField(blank=True)),
                (
                    "block",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="catalog.contentblock",
                    ),
                ),
                (
                    "image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
                (
                    "video",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtaildocs.document",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentCategoryContentBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "block",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="category_links",
                        to="catalog.contentblock",
                    ),
                ),
                (
                    "category",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_blocks",
                        to="catalog.treatmentcategory",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentContentBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "block",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treatment_links",
                        to="catalog.contentblock",
                    ),
                ),
                (
                    "treatment",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_blocks",
                        to="catalog.treatment",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentFAQ",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("question", models.CharField(max_length=200)),
                ("answer", wagtail.fields.RichTextField()),
                (
                    "treatment",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="faqs",
                        to="catalog.treatment",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentFact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("label", models.CharField(max_length=60)),
                ("value", models.CharField(max_length=160)),
                (
                    "treatment",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="facts",
                        to="catalog.treatment",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "usage",
                    models.CharField(
                        choices=[("hero", "Hero"), ("carousel", "Carousel"), ("gallery", "Gallery")],
                        default="hero",
                        max_length=20,
                    ),
                ),
                ("alt_text", models.CharField(blank=True, max_length=160)),
                ("pos_x", models.PositiveSmallIntegerField(default=50)),
                ("pos_y", models.PositiveSmallIntegerField(default=50)),
                ("loop", models.BooleanField(default=True)),
                (
                    "playback_rate",
                    models.CharField(
                        choices=[
                            ("0.75", "0.75x (slow)"),
                            ("1.0", "1.0x (normal)"),
                            ("1.25", "1.25x (fast)"),
                            ("1.5", "1.5x (fast)"),
                        ],
                        default="1.0",
                        max_length=8,
                    ),
                ),
                (
                    "image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
                (
                    "treatment",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media",
                        to="catalog.treatment",
                    ),
                ),
                (
                    "video",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtaildocs.document",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("label", models.CharField(blank=True, max_length=80)),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("currency", models.CharField(blank=True, default="GBP", max_length=10)),
                ("price_text", models.CharField(blank=True, max_length=60)),
                ("description", models.TextField(blank=True)),
                (
                    "targets",
                    models.TextField(
                        blank=True,
                        help_text="One per line. Used to show the treatment targets list.",
                    ),
                ),
                ("notes", models.CharField(blank=True, max_length=240)),
                (
                    "treatment",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prices",
                        to="catalog.treatment",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="TreatmentStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("title", models.CharField(max_length=120)),
                ("body", wagtail.fields.RichTextField()),
                (
                    "treatment",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="catalog.treatment",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
            },
            bases=(models.Model,),
        ),
    ]
