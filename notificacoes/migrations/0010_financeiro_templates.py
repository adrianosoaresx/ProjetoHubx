from django.db import migrations

TEMPLATES = [
    (
        "financeiro_nova_cobranca",
        "Nova cobrança",
        "Você possui uma nova mensalidade de {{ valor }} com vencimento em {{ vencimento }}",
        "email",
    ),
    (
        "financeiro_distribuicao_receita",
        "Receita distribuída",
        "A receita do evento {{ evento }} foi distribuída no valor de {{ valor }}",
        "email",
    ),
    (
        "financeiro_ajuste_lancamento",
        "Ajuste de lançamento",
        "Seu lançamento foi ajustado em {{ valor }}",
        "email",
    ),
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
        ("notificacoes", "0009_alter_notificationlog_status"),
    ]

    operations = [migrations.RunPython(create_templates, delete_templates)]
