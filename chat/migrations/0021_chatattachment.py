# Generated manually for ChatAttachment model
import uuid

import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0020_alter_chatmoderationlog_action"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatAttachment",
            fields=[
                ("deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("arquivo", models.FileField(upload_to="chat/attachments/")),
                ("mime_type", models.CharField(blank=True, max_length=100)),
                ("tamanho", models.PositiveIntegerField(default=0)),
                ("thumb_url", models.URLField(blank=True)),
                ("preview_ready", models.BooleanField(default=False)),
                (
                    "mensagem",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="chat.chatmessage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Anexo",
                "verbose_name_plural": "Anexos",
            },
        )
    ]

