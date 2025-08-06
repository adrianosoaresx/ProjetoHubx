from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0017_chatmessage_reply_to"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatFavorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_favorites", to=settings.AUTH_USER_MODEL)),
                ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorited_by", to="chat.chatmessage")),
            ],
            options={
                "verbose_name": "Favorito",
                "verbose_name_plural": "Favoritos",
                "unique_together": {("user", "message")},
            },
        ),
        migrations.AddIndex(
            model_name="chatfavorite",
            index=models.Index(fields=["user", "message"], name="chatfav_user_msg_idx"),
        ),
    ]
