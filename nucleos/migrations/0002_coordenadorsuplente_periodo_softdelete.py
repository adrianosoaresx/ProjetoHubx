from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nucleos", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="coordenadorsuplente",
            old_name="inicio",
            new_name="periodo_inicio",
        ),
        migrations.RenameField(
            model_name="coordenadorsuplente",
            old_name="fim",
            new_name="periodo_fim",
        ),
        migrations.AddField(
            model_name="coordenadorsuplente",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="coordenadorsuplente",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

