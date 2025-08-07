from django.db import migrations, models
import uuid
import django.db.models.deletion

import core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegracaoConfig",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, default=uuid.uuid4, serialize=False, editable=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=255)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("erp", "ERP"),
                            ("contabilidade", "Contabilidade"),
                            ("gateway", "Gateway de Pagamento"),
                        ],
                        max_length=20,
                    ),
                ),
                ("base_url", core.fields.URLField(max_length=255)),
                (
                    "credenciais_encrypted",
                    core.fields.EncryptedCharField(blank=True, max_length=512),
                ),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Configuração de Integração",
                "verbose_name_plural": "Configurações de Integração",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="IntegracaoIdempotency",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("idempotency_key", models.CharField(max_length=255, unique=True)),
                ("provedor", models.CharField(max_length=100)),
                ("recurso", models.CharField(max_length=100)),
                ("status", models.CharField(max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Idempotência de Integração",
                "verbose_name_plural": "Idempotências de Integração",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="IntegracaoLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, default=uuid.uuid4, serialize=False, editable=False
                    ),
                ),
                ("provedor", models.CharField(max_length=100)),
                ("acao", models.CharField(max_length=100)),
                ("payload_in", models.JSONField(blank=True, default=dict)),
                ("payload_out", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(max_length=50)),
                ("duracao_ms", models.PositiveIntegerField(default=0)),
                ("erro", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Log de Integração",
                "verbose_name_plural": "Logs de Integração",
                "ordering": ["-created_at"],
            },
        ),
    ]
