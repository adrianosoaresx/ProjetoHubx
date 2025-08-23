from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_alter_user_username"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="failed_login_attempts",
        ),
        migrations.RemoveField(
            model_name="user",
            name="lock_expires_at",
        ),
    ]
