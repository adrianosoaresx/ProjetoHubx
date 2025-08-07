from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0022_e2ee_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatchannel",
            name="retencao_dias",
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text="Quantidade de dias para manter mensagens antes da remoção automática",
            ),
        ),
    ]
