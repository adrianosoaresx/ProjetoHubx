import uuid
from django.db import migrations, models


def populate_user_public_id(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all().only("id", "public_id"):
        if not user.public_id:
            user.public_id = uuid.uuid4()
            user.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_remove_user_address_remove_user_facebook_and_more"),
    ]

    operations = [
        # 1) Adiciona o campo permitindo null e sem unique para popular dados existentes
        migrations.AddField(
            model_name="user",
            name="public_id",
            field=models.UUIDField(null=True, blank=True, db_index=True, editable=False),
        ),
        # 2) Popula com UUID únicos
        migrations.RunPython(populate_user_public_id, migrations.RunPython.noop),
        # 3) Torna o campo obrigatório e único, com default para novos registros
        migrations.AlterField(
            model_name="user",
            name="public_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
