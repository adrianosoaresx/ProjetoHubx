from __future__ import annotations

from django.db import migrations

from notificacoes.models import Canal


TEMPLATE_CODES = [
    "connection_request",
    "connection_accepted",
    "connection_declined",
]


def update_channels(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    NotificationTemplate.objects.filter(codigo__in=TEMPLATE_CODES).update(canal=Canal.TODOS)


def revert_channels(apps, schema_editor):
    NotificationTemplate = apps.get_model("notificacoes", "NotificationTemplate")
    NotificationTemplate.objects.filter(codigo__in=TEMPLATE_CODES).update(canal=Canal.PUSH)


class Migration(migrations.Migration):

    dependencies = [
        ("notificacoes", "0012_connection_notification_templates"),
    ]

    operations = [
        migrations.RunPython(update_channels, revert_channels),
    ]
