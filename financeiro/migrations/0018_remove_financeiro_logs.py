from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0017_drop_centrocusto_saldo_column"),
    ]

    operations = [
        migrations.DeleteModel(name="FinanceiroLog"),
        migrations.DeleteModel(name="FinanceiroTaskLog"),
    ]
