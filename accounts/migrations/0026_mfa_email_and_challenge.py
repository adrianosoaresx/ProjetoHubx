from __future__ import annotations

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0025_alter_user_cnpj_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="two_factor_email_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="two_factor_preferred_method",
            field=models.CharField(
                choices=[
                    ("totp", "Aplicativo autenticador"),
                    ("email_otp", "Código por e-mail"),
                ],
                default="totp",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="MFALoginChallenge",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("method", models.CharField(choices=[("email_otp", "Código por e-mail")], max_length=20)),
                (
                    "purpose",
                    models.CharField(
                        choices=[("login", "Login"), ("disable_2fa", "Desativar 2FA")],
                        default="login",
                        max_length=20,
                    ),
                ),
                ("code_hash", models.CharField(max_length=64)),
                ("code_salt", models.CharField(max_length=32)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=5)),
                ("session_key", models.CharField(blank=True, default="", max_length=64)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mfa_login_challenges",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
