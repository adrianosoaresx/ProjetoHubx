from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0019_resumochat"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatmoderationlog",
            name="action",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("approve", "Aprovar"),
                    ("remove", "Remover"),
                    ("edit", "Editar"),
                    ("create_item", "Criar item"),
                ],
            ),
        ),
    ]
