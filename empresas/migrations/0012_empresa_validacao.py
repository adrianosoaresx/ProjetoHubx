from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0011_tag_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="validado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="empresa",
            name="fonte_validacao",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
