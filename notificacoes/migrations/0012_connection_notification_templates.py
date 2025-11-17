from django.db import migrations


TEMPLATES = [
    {
        "codigo": "connection_request",
        "assunto": "Nova solicitação de conexão",
        "corpo": "{{ solicitante }} quer conectar-se com você.",
        "canal": "push",
    },
    {
        "codigo": "connection_accepted",
        "assunto": "Solicitação de conexão aceita",
        "corpo": "{{ solicitado }} aceitou sua solicitação de conexão.",
        "canal": "push",
    },
    {
        "codigo": "connection_declined",
        "assunto": "Solicitação de conexão recusada",
        "corpo": "{{ solicitado }} recusou sua solicitação de conexão.",
        "canal": "push",
    },
]


def create_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    for template in TEMPLATES:
        NotificationTemplate.objects.get_or_create(
            codigo=template["codigo"],
            defaults=template,
        )


def remove_templates(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    NotificationTemplate.objects.filter(codigo__in=[tpl["codigo"] for tpl in TEMPLATES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notificacoes", "0011_feed_share_template"),
    ]

    operations = [
        migrations.RunPython(create_templates, remove_templates),
    ]
