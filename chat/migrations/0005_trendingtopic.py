from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0004_alter_chatmoderationlog_action"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrendingTopic",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("palavra", models.CharField(max_length=100)),
                ("frequencia", models.PositiveIntegerField()),
                ("periodo_inicio", models.DateTimeField()),
                ("periodo_fim", models.DateTimeField()),
                (
                    "canal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trending_topics",
                        to="chat.chatchannel",
                    ),
                ),
            ],
            options={
                "ordering": ["-frequencia"],
                "verbose_name": "Tópico em Alta",
                "verbose_name_plural": "Tópicos em Alta",
            },
        ),
    ]
