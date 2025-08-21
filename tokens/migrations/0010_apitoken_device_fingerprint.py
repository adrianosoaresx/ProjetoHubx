from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0009_alter_apitoken_expires_at"),
        ("tokens", "0009_codigoautenticacaolog"),
    ]

    operations = [
        migrations.AddField(
            model_name="apitoken",
            name="device_fingerprint",
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]

