from __future__ import annotations

import string

from django.db import migrations


def _is_sha256_hex(value: str | None) -> bool:
    if not value or len(value) != 64:
        return False
    hex_digits = set(string.hexdigits)
    return all(char in hex_digits for char in value)


def normalize(value: str) -> str:
    return value.strip().replace(" ", "").upper()


def forwards(apps, schema_editor):
    TOTPDevice = apps.get_model("tokens", "TOTPDevice")

    for device in TOTPDevice.objects.select_related("usuario").all():
        secret = getattr(device, "secret", "")
        if not _is_sha256_hex(secret):
            continue
        user = getattr(device, "usuario", None)
        user_secret = getattr(user, "two_factor_secret", None) if user else None
        if user_secret:
            device.secret = normalize(user_secret)
            device.save(update_fields=["secret"])


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0019_tokenacesso_codigo_preview"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
