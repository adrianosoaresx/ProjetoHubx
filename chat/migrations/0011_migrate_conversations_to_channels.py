from django.db import migrations
import uuid


def forwards(apps, schema_editor):
    ChatConversation = apps.get_model('chat', 'ChatConversation')
    ChatChannel = apps.get_model('chat', 'ChatChannel')
    ChatMessage = apps.get_model('chat', 'ChatMessage')
    ChatParticipant = apps.get_model('chat', 'ChatParticipant')

    conv_to_channel = {}
    for conv in ChatConversation.objects.all():
        ch = ChatChannel.objects.create(
            id=uuid.uuid4(),
            contexto_tipo=conv.tipo_conversa,
            contexto_id=conv.nucleo_id or conv.evento_id or conv.organizacao_id,
            titulo=conv.titulo or "",
            descricao=getattr(conv, 'descricao', "") or "",
        )
        conv_to_channel[conv.id] = ch

    for msg in ChatMessage.objects.all():
        old_conv_id = getattr(msg, 'conversation_id', None)
        if old_conv_id and old_conv_id in conv_to_channel:
            msg.channel = conv_to_channel[old_conv_id]
            msg.save(update_fields=['channel'])

    for part in ChatParticipant.objects.all():
        old_conv_id = getattr(part, 'conversation_id', None)
        if old_conv_id and old_conv_id in conv_to_channel:
            part.channel = conv_to_channel[old_conv_id]
            part.save(update_fields=['channel'])


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0010_relatoriochatexport_status_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
