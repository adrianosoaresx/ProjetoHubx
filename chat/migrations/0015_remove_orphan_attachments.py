from django.db import migrations


def remove_orphan_attachments(apps, schema_editor):
    ChatAttachment = apps.get_model('chat', 'ChatAttachment')
    ChatAttachment.objects.filter(mensagem__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0014_relatoriochatexport_arquivo_path'),
    ]

    operations = [
        migrations.RunPython(remove_orphan_attachments, migrations.RunPython.noop),
    ]
