from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0012_remove_inscricaoevento_avaliacao"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventoLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("acao", models.CharField(max_length=50)),
                ("detalhes", models.JSONField(blank=True, default=dict)),
                ("evento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="agenda.evento")),
                ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created"]},
        ),
        migrations.AddField(
            model_name="briefingevento",
            name="coordenadora_aprovou",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="briefingevento",
            name="prazo_limite_resposta",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="briefingevento",
            name="recusado_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="briefings_recusados", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="historicalbriefingevento",
            name="coordenadora_aprovou",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="historicalbriefingevento",
            name="prazo_limite_resposta",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalbriefingevento",
            name="recusado_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+historical_briefings_recusados", to=settings.AUTH_USER_MODEL),
        ),
    ]
