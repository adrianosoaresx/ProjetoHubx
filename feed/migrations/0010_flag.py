# Generated manually for Flag model
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("feed", "0009_search_indexes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Flag",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="flags", to="feed.post")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="flags", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Denúncia",
                "verbose_name_plural": "Denúncias",
                "unique_together": {("post", "user")},
            },
        ),
    ]
