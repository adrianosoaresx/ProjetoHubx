from django.db import migrations, models
from django.utils.text import slugify

def migrate_participacoes(apps, schema_editor):
    Participacao = apps.get_model('nucleos', 'ParticipacaoNucleo')
    for p in Participacao.objects.all():
        p.papel = 'coordenador' if getattr(p, 'is_coordenador', False) else 'membro'
        if p.status == 'aprovado':
            p.status = 'ativo'
        elif p.status == 'recusado':
            p.status = 'inativo'
        p.save(update_fields=['papel', 'status'])


def migrate_nucleos(apps, schema_editor):
    Nucleo = apps.get_model('nucleos', 'Nucleo')
    for n in Nucleo.objects.all():
        n.ativo = not getattr(n, 'inativa', False)
        if not n.slug:
            n.slug = slugify(n.nome)
        n.save(update_fields=['ativo', 'slug'])


class Migration(migrations.Migration):
    dependencies = [
        ('nucleos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nucleo',
            name='ativo',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='nucleo',
            name='slug',
            field=models.SlugField(max_length=255, blank=True),
        ),
        migrations.AddConstraint(
            model_name='nucleo',
            constraint=models.UniqueConstraint(fields=('organizacao', 'slug'), name='uniq_org_slug'),
        ),
        migrations.AddField(
            model_name='participacaonucleo',
            name='papel',
            field=models.CharField(default='membro', max_length=20),
        ),
        migrations.AlterField(
            model_name='participacaonucleo',
            name='status',
            field=models.CharField(default='pendente', max_length=20, db_index=True),
        ),
        migrations.RunPython(migrate_participacoes, migrations.RunPython.noop),
        migrations.RunPython(migrate_nucleos, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='nucleo',
            name='inativa',
        ),
        migrations.RemoveField(
            model_name='nucleo',
            name='inativada_em',
        ),
        migrations.RemoveField(
            model_name='participacaonucleo',
            name='is_coordenador',
        ),
    ]
