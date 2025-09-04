import uuid
from django.db import migrations, models


def populate_nucleo_public_id(apps, schema_editor):
    Nucleo = apps.get_model("nucleos", "Nucleo")
    for nucleo in Nucleo.objects.all().only("id", "public_id"):
        if not nucleo.public_id:
            nucleo.public_id = uuid.uuid4()
            nucleo.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("nucleos", "0008_nucleo_ativo"),
    ]

    operations = [
        migrations.AddField(
            model_name="nucleo",
            name="public_id",
            field=models.UUIDField(null=True, blank=True, db_index=True, editable=False),
        ),
        migrations.RunPython(populate_nucleo_public_id, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="nucleo",
            name="public_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
