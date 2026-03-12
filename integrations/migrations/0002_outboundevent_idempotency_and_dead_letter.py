from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboundevent",
            name="idempotency_key",
            field=models.CharField(blank=True, db_index=True, default="", max_length=128),
        ),
        migrations.AlterField(
            model_name="outboundevent",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("sent", "Sent"),
                    ("failed", "Failed"),
                    ("dead_letter", "Dead letter"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
            ),
        ),
    ]
