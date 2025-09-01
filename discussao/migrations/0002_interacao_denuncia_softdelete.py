from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discussao", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="interacaodiscussao",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="interacaodiscussao",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="denuncia",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="denuncia",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
