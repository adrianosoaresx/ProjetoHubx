from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("eventos", "0004_inscricao_avaliacao_constraint"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="inscricaoevento",
            name="inscricao_avaliacao_valida",
        ),
        migrations.RemoveField(
            model_name="inscricaoevento",
            name="avaliacao",
        ),
        migrations.RemoveField(
            model_name="inscricaoevento",
            name="feedback",
        ),
    ]
