from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0012_merge_20250814_2013"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="alg",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="key_version",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="chatmessage",
            name="conteudo",
            field=models.TextField(blank=True, null=True),
        ),
    ]

