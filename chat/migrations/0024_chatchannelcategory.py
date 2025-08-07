from django.db import migrations, models
import uuid
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0023_chatchannel_retencao_dias"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatChannelCategory",
            fields=[
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                ("nome", models.CharField(max_length=100, unique=True)),
                ("descricao", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Categoria de Canal",
                "verbose_name_plural": "Categorias de Canal",
            },
        ),
        migrations.AddField(
            model_name="chatchannel",
            name="categoria",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="channels",
                to="chat.chatchannelcategory",
            ),
        ),
    ]
