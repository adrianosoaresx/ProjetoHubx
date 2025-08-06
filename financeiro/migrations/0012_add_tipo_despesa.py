from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0011_lancamento_compound_index"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lancamentofinanceiro",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("mensalidade_associacao", "Mensalidade Associação"),
                    ("mensalidade_nucleo", "Mensalidade Núcleo"),
                    ("ingresso_evento", "Ingresso Evento"),
                    ("aporte_interno", "Aporte Interno"),
                    ("aporte_externo", "Aporte Externo"),
                    ("despesa", "Despesa"),
                ],
                max_length=32,
            ),
        ),
    ]
