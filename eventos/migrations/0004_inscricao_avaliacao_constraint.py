from django.db import migrations, models
from django.db.models import Q


def limpar_avaliacoes_invalidas(apps, schema_editor):
    InscricaoEvento = apps.get_model('eventos', 'InscricaoEvento')
    InscricaoEvento.objects.filter(
        avaliacao__isnull=False
    ).exclude(avaliacao__gte=1, avaliacao__lte=5).update(avaliacao=None)


class Migration(migrations.Migration):

    dependencies = [
        ("eventos", "0003_alter_eventolog_options_alter_tarefalog_options_and_more"),
    ]

    operations = [
        migrations.RunPython(limpar_avaliacoes_invalidas, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="inscricaoevento",
            constraint=models.CheckConstraint(
                check=Q(avaliacao__gte=1, avaliacao__lte=5) | Q(avaliacao__isnull=True),
                name="inscricao_avaliacao_valida",
            ),
        ),
    ]
