from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("discussao", "0002_interacao_denuncia_softdelete"),
    ]

    operations = [
        migrations.RenameField(
            model_name="categoriadiscussao",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="categoriadiscussao",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="categoriadiscussao",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="categoriadiscussao",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="tag",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="tag",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="tag",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="tag",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="topicodiscussao",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="topicodiscussao",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="topicodiscussao",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="topicodiscussao",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="respostadiscussao",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="respostadiscussao",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="respostadiscussao",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="respostadiscussao",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="interacaodiscussao",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="interacaodiscussao",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="interacaodiscussao",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="interacaodiscussao",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="denuncia",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="denuncia",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="denuncia",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="denuncia",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="discussionmoderationlog",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="discussionmoderationlog",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="discussionmoderationlog",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="discussionmoderationlog",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name="topicodiscussao",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Tópico de Discussão",
                "verbose_name_plural": "Tópicos de Discussão",
                "indexes": [models.Index(fields=["slug", "categoria"], name="discussao_t_slug_f19f97_idx")],
            },
        ),
        migrations.AlterModelOptions(
            name="respostadiscussao",
            options={
                "ordering": ["created_at"],
                "verbose_name": "Resposta de Discussão",
                "verbose_name_plural": "Respostas de Discussão",
            },
        ),
    ]
