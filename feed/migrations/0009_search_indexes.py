from django.db import migrations
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):
    dependencies = [
        ("feed", "0008_alter_post_conteudo"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="post",
            index=GinIndex(fields=["conteudo"], name="post_conteudo_gin"),
        ),
        migrations.AddIndex(
            model_name="tag",
            index=GinIndex(fields=["nome"], name="tag_nome_gin"),
        ),
    ]
