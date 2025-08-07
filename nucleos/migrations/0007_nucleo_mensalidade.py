from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ("nucleos", "0006_convitenucleo"),
    ]

    operations = [
        migrations.AddField(
            model_name="nucleo",
            name="mensalidade",
            field=models.DecimalField(default=Decimal("30.00"), max_digits=8, decimal_places=2),
        ),
    ]
