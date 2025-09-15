from django.db import migrations


def create_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    templates = [
        {
            "codigo": "feed_like",
            "assunto": "Seu post recebeu uma curtida",
            "corpo": "Alguém curtiu seu post.",
            "canal": "push",
        },
        {
            "codigo": "feed_comment",
            "assunto": "Seu post recebeu um comentário",
            "corpo": "Alguém comentou no seu post.",
            "canal": "push",
        },
    ]

    for template in templates:
        NotificationTemplate.objects.get_or_create(
            codigo=template["codigo"],
            defaults=template,
        )


def remove_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    NotificationTemplate.objects.filter(codigo__in=["feed_like", "feed_comment"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notificacoes", "0009_feed_new_post_template"),
    ]

    operations = [
        migrations.RunPython(create_templates, remove_templates),
    ]
