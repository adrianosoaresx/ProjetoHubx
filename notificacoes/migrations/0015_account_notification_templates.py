from django.db import migrations


TEMPLATES = [
    {
        "codigo": "email_confirmation",
        "assunto": "Confirme seu e-mail",
        "corpo": "Olá {{ nome }}, confirme seu e-mail acessando: {{ url }}",
        "canal": "email",
    },
    {
        "codigo": "password_reset",
        "assunto": "Redefina sua senha",
        "corpo": "Olá {{ nome }}, redefina sua senha acessando: {{ url }}",
        "canal": "email",
    },
    {
        "codigo": "cancel_delete",
        "assunto": "Cancelamento de exclusão",
        "corpo": "Olá {{ nome }}, cancele a exclusão da sua conta acessando: {{ url }}",
        "canal": "email",
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
        ("notificacoes", "0014_notificationlog_context_and_more"),
    ]

    operations = [
        migrations.RunPython(create_templates, remove_templates),
    ]
