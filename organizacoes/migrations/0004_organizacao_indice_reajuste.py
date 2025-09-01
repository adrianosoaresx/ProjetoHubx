from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('organizacoes', '0003_remove_organizacao_inativa_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizacao',
            name='indice_reajuste',
            field=models.DecimalField(default=Decimal('0'), max_digits=5, decimal_places=4, help_text='Índice de reajuste anual'),
        ),
    ]
