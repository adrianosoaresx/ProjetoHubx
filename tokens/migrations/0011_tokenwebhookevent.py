import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0010_merge_20250910_0000"),
    ]

    operations = [
        migrations.CreateModel(
            name="TokenWebhookEvent",
            fields=[
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("url", models.URLField()),
                ("payload", models.JSONField()),
                ("delivered", models.BooleanField(default=False)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
