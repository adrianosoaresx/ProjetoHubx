from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agenda", "0016_inscricaoevento_avaliacao_inscricaoevento_feedback"),
        ("chat", "0019_resumochat"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="mensagem_origem",
            field=models.ForeignKey(
                to="chat.ChatMessage",
                on_delete=models.SET_NULL,
                null=True,
                blank=True,
                related_name="eventos_criados",
            ),
        ),
    ]
