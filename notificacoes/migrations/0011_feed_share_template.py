from django.db import migrations


TEMPLATE_CODE = "feed_share"


def create_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    NotificationTemplate.objects.get_or_create(
        codigo=TEMPLATE_CODE,
        defaults={
            "assunto": "Seu post foi compartilhado",
            "corpo": "Alguém compartilhou seu post.",
            "canal": "push",
        },
    )


def remove_template(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    NotificationTemplate.objects.filter(codigo=TEMPLATE_CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notificacoes", "0010_feed_interaction_templates"),
    ]

    operations = [
        migrations.RunPython(create_template, remove_template),
    ]
