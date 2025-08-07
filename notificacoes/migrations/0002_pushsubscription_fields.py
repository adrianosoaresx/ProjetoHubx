from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notificacoes", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="pushsubscription",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="pushsubscription",
            name="token",
        ),
        migrations.AddField(
            model_name="pushsubscription",
            name="device_id",
            field=models.CharField(max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pushsubscription",
            name="endpoint",
            field=models.CharField(max_length=500, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pushsubscription",
            name="p256dh",
            field=models.CharField(max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pushsubscription",
            name="auth",
            field=models.CharField(max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pushsubscription",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="pushsubscription",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterUniqueTogether(
            name="pushsubscription",
            unique_together={("user", "device_id")},
        ),
    ]
