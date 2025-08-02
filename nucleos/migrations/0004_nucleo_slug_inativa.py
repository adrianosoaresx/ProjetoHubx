import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nucleos", "0003_nucleo_membros"),
    ]

    operations = [
        migrations.AddField(
            model_name="nucleo",
            name="slug",
            field=models.SlugField(max_length=255, unique=True, default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name="nucleo",
            name="inativa",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="nucleo",
            name="inativada_em",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]

