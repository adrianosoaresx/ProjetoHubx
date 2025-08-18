from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_achievement_deleted_achievement_deleted_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MetricDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("titulo", models.CharField(max_length=100)),
                ("descricao", models.TextField(blank=True)),
                ("provider", models.CharField(max_length=100)),
                ("params", models.JSONField(blank=True, default=dict)),
                ("publico", models.BooleanField(default=False)),
                ("ativo", models.BooleanField(default=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metric_definitions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
