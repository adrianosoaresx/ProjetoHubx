from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("eventos", "0035_inscricaoevento_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="inscricaoevento",
            name="condicao_faturamento",
            field=models.CharField(
                blank=True,
                choices=[("avista", "À vista"), ("2x", "2x"), ("3x", "3x")],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="inscricaoevento",
            name="metodo_pagamento",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pix", "Pix"),
                    ("boleto", "Boleto"),
                    ("card", "Cartão de crédito"),
                    ("faturamento", "Faturamento interno"),
                    ("faturar_avista", "Faturar à vista"),
                    ("faturar_2x", "Faturar em 2x"),
                    ("faturar_3x", "Faturar em 3x"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
