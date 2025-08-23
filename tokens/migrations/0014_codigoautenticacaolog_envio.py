from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0013_alter_tokenusolog_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="codigoautenticacaolog",
            name="status_envio",
            field=models.CharField(
                choices=[("sucesso", "Sucesso"), ("falha", "Falha")],
                max_length=20,
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="codigoautenticacaolog",
            name="mensagem_envio",
            field=models.TextField(null=True, blank=True),
        ),
    ]
