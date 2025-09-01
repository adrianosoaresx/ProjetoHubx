from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0002_dashboard_timestamp"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardCustomMetric",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now, editable=False),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("nome", models.CharField(max_length=100)),
                ("descricao", models.TextField(blank=True)),
                ("query_spec", models.JSONField()),
                (
                    "escopo",
                    models.CharField(
                        choices=[
                            ("global", "global"),
                            ("organizacao", "organizacao"),
                            ("nucleo", "nucleo"),
                            ("evento", "evento"),
                        ],
                        max_length=20,
                    ),
                ),
            ],
            options={"get_latest_by": "updated_at"},
        ),
    ]

