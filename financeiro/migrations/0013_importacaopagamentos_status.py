from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0012_add_tipo_despesa"),
    ]

    operations = [
        migrations.AddField(
            model_name="importacaopagamentos",
            name="status",
            field=models.CharField(
                choices=[
                    ("processando", "Em processamento"),
                    ("concluido", "Concluído"),
                    ("erro", "Erro"),
                ],
                default="processando",
                max_length=20,
            ),
        ),
    ]
