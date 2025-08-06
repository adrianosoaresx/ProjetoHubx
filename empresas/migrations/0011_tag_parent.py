from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0010_empresa_versao_favoritoempresa"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="parent",
            field=models.ForeignKey(
                to="empresas.tag",
                related_name="children",
                null=True,
                blank=True,
                on_delete=models.SET_NULL,
            ),
        ),
    ]
