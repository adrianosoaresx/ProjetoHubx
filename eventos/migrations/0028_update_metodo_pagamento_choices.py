from django.db import migrations, models


def forwards_update_faturar_choices(apps, schema_editor):
    InscricaoEvento = apps.get_model("eventos", "InscricaoEvento")
    InscricaoEvento.objects.filter(metodo_pagamento="faturar").update(
        metodo_pagamento="faturar_avista"
    )


def backwards_restore_faturar_choice(apps, schema_editor):
    InscricaoEvento = apps.get_model("eventos", "InscricaoEvento")
    InscricaoEvento.objects.filter(
        metodo_pagamento__in=[
            "faturar_avista",
            "faturar_2x",
            "faturar_3x",
        ]
    ).update(metodo_pagamento="faturar")


class Migration(migrations.Migration):

    dependencies = [
        ("eventos", "0027_remove_inscricaoevento_observacao_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inscricaoevento",
            name="metodo_pagamento",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pix", "Pix"),
                    ("boleto", "Boleto"),
                    ("faturar_avista", "Faturar à vista"),
                    ("faturar_2x", "Faturar em 2x"),
                    ("faturar_3x", "Faturar em 3x"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(
            forwards_update_faturar_choices,
            backwards_restore_faturar_choice,
        ),
    ]
