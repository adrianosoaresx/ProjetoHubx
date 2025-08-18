from __future__ import annotations

import base64
import hashlib
import secrets
from django.db import migrations, models


def forwards(apps, schema_editor):
    TokenAcesso = apps.get_model("tokens", "TokenAcesso")
    for token in TokenAcesso.objects.all():
        codigo = getattr(token, "codigo", "")
        if not codigo:
            continue
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", codigo.encode(), salt, 120000)
        token.codigo_salt = base64.b64encode(salt).decode()
        token.codigo_hash = base64.b64encode(digest).decode()
        token.save(update_fields=["codigo_salt", "codigo_hash"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0004_merge_20250814_1958"),
    ]

    operations = [
        migrations.AddField(
            model_name="tokenacesso",
            name="codigo_hash",
            field=models.CharField(max_length=64, unique=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tokenacesso",
            name="codigo_salt",
            field=models.CharField(max_length=32, default=""),
            preserve_default=False,
        ),
        migrations.RunPython(forwards, noop),
        migrations.RemoveField(
            model_name="tokenacesso",
            name="codigo",
        ),
    ]
