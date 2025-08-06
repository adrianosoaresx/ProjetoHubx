from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feed", "0006_alter_moderacaopost_avaliado_em_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="post",
            name="deleted_at",
        ),
        migrations.AddField(
            model_name="post",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
