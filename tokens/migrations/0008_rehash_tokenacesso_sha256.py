from __future__ import annotations

import base64
import hashlib
from django.db import migrations


def forwards(apps, schema_editor):
    TokenAcesso = apps.get_model("tokens", "TokenAcesso")
    for token in TokenAcesso.objects.exclude(codigo_salt=""):
        try:
            raw_hash = base64.b64decode(token.codigo_hash)
        except Exception:
            raw_hash = token.codigo_hash.encode()
        token.codigo_hash = hashlib.sha256(raw_hash).hexdigest()
        token.codigo_salt = ""
        token.save(update_fields=["codigo_hash", "codigo_salt"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0007_merge_20250818_2117"),
    ]

    operations = [
        migrations.RunPython(forwards, noop),
    ]
