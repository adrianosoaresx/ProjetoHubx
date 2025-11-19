from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ai_chat", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="chatmessage",
            name="chatmessage_organizacao_matches_session",
        ),
    ]
