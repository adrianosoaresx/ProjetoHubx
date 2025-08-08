from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_initial_achievements(apps, schema_editor):
    Achievement = apps.get_model('dashboard', 'Achievement')
    Achievement.objects.create(
        code='100_inscricoes',
        titulo='Participante Assíduo',
        descricao='Realizou 100 inscrições em eventos.',
        criterio='Atingir 100 inscrições em eventos',
        icon='trophy',
    )
    Achievement.objects.create(
        code='5_dashboards',
        titulo='Explorador de Dashboards',
        descricao='Criou 5 dashboards personalizados.',
        criterio='Criar 5 dashboards personalizados',
        icon='chart-bar',
    )


def remove_initial_achievements(apps, schema_editor):
    Achievement = apps.get_model('dashboard', 'Achievement')
    Achievement.objects.filter(code__in=['100_inscricoes', '5_dashboards']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('titulo', models.CharField(max_length=100)),
                ('descricao', models.TextField()),
                ('criterio', models.CharField(max_length=200)),
                ('icon', models.CharField(blank=True, max_length=200)),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='UserAchievement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('completado_em', models.DateTimeField(auto_now_add=True)),
                ('achievement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.achievement')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'unique_together': {('user', 'achievement')}},
        ),
        migrations.RunPython(create_initial_achievements, remove_initial_achievements),
    ]
