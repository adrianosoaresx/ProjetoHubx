import hashlib
from django.db import migrations


def hash_secrets(apps, schema_editor):
    TOTPDevice = apps.get_model('tokens', 'TOTPDevice')
    for device in TOTPDevice.objects.all():
        secret = getattr(device, 'secret', None)
        if secret and len(secret) != 64:
            device.secret = hashlib.sha256(secret.encode()).hexdigest()
            device.save(update_fields=['secret'])


class Migration(migrations.Migration):
    dependencies = [
        ('tokens', '0006_codigoautenticacao_hash_totpdevice_encrypt'),
    ]

    operations = [
        migrations.RunPython(hash_secrets, migrations.RunPython.noop),
    ]
