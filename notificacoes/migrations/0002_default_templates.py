from django.db import migrations

TEMPLATES = [
    ("password_reset", "Redefini\u00e7\u00e3o de Senha", "Acesse o link: {{ url }}", "email"),
    ("email_confirmation", "Confirma\u00e7\u00e3o de Email", "Clique para confirmar: {{ url }}", "email"),
    ("cobranca_pendente", "Cobran\u00e7a pendente", "Existe um lan\u00e7amento pendente de pagamento.", "email"),
    ("inadimplencia", "Inadimpl\u00eancia", "Voc\u00ea possui lan\u00e7amentos vencidos.", "email"),
]


def create_templates(apps, schema_editor):
    Template = apps.get_model("notificacoes", "NotificationTemplate")
    for code, subject, body, canal in TEMPLATES:
        Template.objects.get_or_create(codigo=code, defaults={"assunto": subject, "corpo": body, "canal": canal})


def delete_templates(apps, schema_editor):
    Template = apps.get_model("notificacoes", "NotificationTemplate")
    Template.objects.filter(codigo__in=[t[0] for t in TEMPLATES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notificacoes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_templates, delete_templates),
    ]
