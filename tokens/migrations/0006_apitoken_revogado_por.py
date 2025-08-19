from __future__ import annotations

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0005_tokens_hardening"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="apitoken",
            name="revogado_por",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
                related_name="api_tokens_revogados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
