from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("configuracoes", "0002_configuracaocontalog_updated_at_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="configuracaoconta",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="configuracaoconta",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterModelOptions(
            name="configuracaoconta",
            options={
                "ordering": ["-updated_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["user"],
                        name="configuracao_conta_user_unique",
                    )
                ],
            },
        ),
        migrations.RenameField(
            model_name="configuracaocontextual",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="configuracaocontextual",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterModelOptions(
            name="configuracaocontextual",
            options={
                "ordering": ["-updated_at"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["user", "escopo_tipo", "escopo_id"],
                        name="config_contextual_user_scope_unique",
                    )
                ],
            },
        ),
    ]
