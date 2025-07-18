from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('discussao', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL('DROP TABLE IF EXISTS forum_topico;'),
        migrations.RunSQL('DROP TABLE IF EXISTS forum_resposta;'),
    ]
