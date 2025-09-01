import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_remove_chatmessagereaction_created_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="chatparticipant",
            name="created",
        ),
        migrations.RemoveField(
            model_name="chatparticipant",
            name="modified",
        ),
        migrations.AddField(
            model_name="chatparticipant",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name="chatparticipant",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="chatparticipant",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="chatparticipant",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="chatparticipant",
            unique_together={("user", "channel", "deleted")},
        ),
        migrations.RemoveField(
            model_name="chatfavorite",
            name="created",
        ),
        migrations.RemoveField(
            model_name="chatfavorite",
            name="modified",
        ),
        migrations.AddField(
            model_name="chatfavorite",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name="chatfavorite",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="chatfavorite",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="chatfavorite",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="chatfavorite",
            unique_together={("user", "message", "deleted")},
        ),
        migrations.RemoveIndex(
            model_name="chatfavorite",
            name="chat_chatfa_user_id_7580ff_idx",
        ),
        migrations.AddIndex(
            model_name="chatfavorite",
            index=models.Index(fields=["user", "message", "deleted"], name="chat_chatfa_user_id_7580ff_idx"),
        ),
        migrations.RemoveField(
            model_name="relatoriochatexport",
            name="created",
        ),
        migrations.RemoveField(
            model_name="relatoriochatexport",
            name="modified",
        ),
        migrations.AddField(
            model_name="relatoriochatexport",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name="relatoriochatexport",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
