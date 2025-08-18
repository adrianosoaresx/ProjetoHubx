from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notificacoes", "0004_remove_notificationtemplate_ativo_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pushsubscription",
            name="ativo",
            field=models.BooleanField(default=True),
        ),
    ]
