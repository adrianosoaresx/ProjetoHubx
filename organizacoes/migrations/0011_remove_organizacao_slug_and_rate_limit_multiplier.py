from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("organizacoes", "0010_organizacao_chave_pix"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="organizacao",
            name="rate_limit_multiplier",
        ),
        migrations.RemoveField(
            model_name="organizacao",
            name="slug",
        ),
    ]
