from django.db import migrations, models
import django.utils.timezone


def migrate_loginattempt_timestamp(apps, schema_editor):
    LoginAttempt = apps.get_model("accounts", "LoginAttempt")
    for obj in LoginAttempt.objects.all():
        ts = obj.timestamp
        obj.created_at = ts
        obj.updated_at = ts
        obj.save(update_fields=["created_at", "updated_at"])

def migrate_securityevent_timestamp(apps, schema_editor):
    SecurityEvent = apps.get_model("accounts", "SecurityEvent")
    for obj in SecurityEvent.objects.all():
        ts = obj.timestamp
        obj.created_at = ts
        obj.updated_at = ts
        obj.save(update_fields=["created_at", "updated_at"])

def set_user_deleted(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(deleted_at__isnull=False).update(deleted=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_user_email_confirmed"),
    ]

    operations = [
        migrations.AddField(
            model_name="accounttoken",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="accounttoken",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="loginattempt",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name="loginattempt",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="loginattempt",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="loginattempt",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.RunPython(migrate_loginattempt_timestamp, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="loginattempt",
            name="timestamp",
        ),
        migrations.AddField(
            model_name="mediatag",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="mediatag",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="securityevent",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name="securityevent",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="securityevent",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="securityevent",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.RunPython(migrate_securityevent_timestamp, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="securityevent",
            name="timestamp",
        ),
        migrations.AddField(
            model_name="user",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_user_deleted, migrations.RunPython.noop),
        migrations.AddField(
            model_name="usermedia",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="usermedia",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
