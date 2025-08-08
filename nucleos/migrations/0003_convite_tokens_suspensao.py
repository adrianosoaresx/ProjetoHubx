from datetime import timedelta

import django.db.models.deletion
from django.db import migrations, models


def set_convite_expiration(apps, schema_editor):
    Convite = apps.get_model('nucleos', 'ConviteNucleo')
    for convite in Convite.objects.all():
        if not convite.data_expiracao:
            convite.data_expiracao = convite.criado_em + timedelta(days=7)
            convite.save(update_fields=['data_expiracao'])

class Migration(migrations.Migration):

    dependencies = [
        ('nucleos', '0002_refatoracao'),
        ('tokens', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='convitenucleo',
            name='token_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='convites_nucleo', db_column='token_id', to='tokens.tokenacesso'),
        ),
        migrations.AddField(
            model_name='convitenucleo',
            name='data_expiracao',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='convitenucleo',
            name='limite_uso_diario',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='participacaonucleo',
            name='status_suspensao',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='participacaonucleo',
            name='data_suspensao',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(set_convite_expiration, migrations.RunPython.noop),
    ]
