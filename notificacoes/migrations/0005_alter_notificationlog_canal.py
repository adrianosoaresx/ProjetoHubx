from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notificacoes", "0004_remove_notificationtemplate_ativo_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notificationlog",
            name="canal",
            field=models.CharField(
                max_length=20,
                choices=[("email", "E-mail"), ("push", "Push"), ("whatsapp", "WhatsApp")],
            ),
        ),
    ]
