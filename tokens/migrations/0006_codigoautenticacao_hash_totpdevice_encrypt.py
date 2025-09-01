from __future__ import annotations

import base64
import hashlib
import secrets

import core.fields
from django.db import migrations, models


def hash_existing_codes(apps, schema_editor):
    CodigoAutenticacao = apps.get_model("tokens", "CodigoAutenticacao")
    for codigo in CodigoAutenticacao.objects.all():
        raw = getattr(codigo, "codigo", "")
        if not raw:
            continue
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt, 120000)
        codigo.codigo_salt = base64.b64encode(salt).decode()
        codigo.codigo_hash = base64.b64encode(digest).decode()
        codigo.save(update_fields=["codigo_salt", "codigo_hash"])


def encrypt_totp_secrets(apps, schema_editor):
    TOTPDevice = apps.get_model("tokens", "TOTPDevice")
    for device in TOTPDevice.objects.all():
        secret = device.secret
        if secret and not secret.startswith("gAAAA"):
            device.secret = secret
            device.save(update_fields=["secret"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0005_tokens_hardening"),
    ]

    operations = [
        migrations.AddField(
            model_name="codigoautenticacao",
            name="codigo_hash",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="codigoautenticacao",
            name="codigo_salt",
            field=models.CharField(default="", max_length=32),
            preserve_default=False,
        ),
        migrations.RunPython(hash_existing_codes, noop),
        migrations.RemoveField(
            model_name="codigoautenticacao",
            name="codigo",
        ),
        migrations.AlterField(
            model_name="totpdevice",
            name="secret",
            field=core.fields.EncryptedCharField(max_length=128),
        ),
        migrations.RunPython(encrypt_totp_secrets, noop),
    ]
