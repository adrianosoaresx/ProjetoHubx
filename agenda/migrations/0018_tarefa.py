from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0017_evento_mensagem_origem'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organizacoes', '0008_organizacaoatividadelog_organizacaochangelog_and_more'),
        ('nucleos', '0006_convitenucleo'),
        ('chat', '0023_chatchannel_retencao_dias'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tarefa',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ('titulo', models.CharField(max_length=150)),
                ('descricao', models.TextField(blank=True)),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField()),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('concluida', 'Concluída')], default='pendente', max_length=20)),
                ('organizacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organizacoes.organizacao')),
                ('nucleo', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to='nucleos.nucleo')),
                ('mensagem_origem', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tarefas', to='chat.chatmessage')),
                ('responsavel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tarefas_criadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tarefa',
                'verbose_name_plural': 'Tarefas',
            },
        ),
        migrations.CreateModel(
            name='TarefaLog',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(max_length=50)),
                ('detalhes', models.JSONField(blank=True, default=dict, encoder=DjangoJSONEncoder)),
                ('tarefa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='agenda.tarefa')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Log de Tarefa',
                'verbose_name_plural': 'Logs de Tarefa',
            },
        ),
    ]
