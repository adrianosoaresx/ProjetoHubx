from __future__ import annotations

from datetime import time

from django.db import migrations, models


def migrate_tema(apps, schema_editor):
    Config = apps.get_model('configuracoes', 'ConfiguracaoConta')
    for config in Config.objects.all():
        if getattr(config, 'tema_escuro', False):
            config.tema = 'escuro'
            config.save(update_fields=['tema'])


class Migration(migrations.Migration):

    dependencies = [
        ('configuracoes', '0005_configuracaoconta_deleted_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaoconta',
            name='hora_notificacao_diaria',
            field=models.TimeField(default=time(8, 0), help_text='Horário para envio de notificações diárias'),
        ),
        migrations.AddField(
            model_name='configuracaoconta',
            name='hora_notificacao_semanal',
            field=models.TimeField(default=time(8, 0), help_text='Horário para envio de notificações semanais'),
        ),
        migrations.AddField(
            model_name='configuracaoconta',
            name='dia_semana_notificacao',
            field=models.PositiveSmallIntegerField(default=0, help_text='Dia da semana para notificações semanais'),
        ),
        migrations.RunPython(migrate_tema),
        migrations.RemoveField(
            model_name='configuracaoconta',
            name='tema_escuro',
        ),
    ]
