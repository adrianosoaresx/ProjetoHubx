from django.db import migrations
import django_extensions.db.fields


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0004_empresa_empresas_em_deleted_e09a62_idx"),
    ]

    operations = [
        migrations.RenameField(
            model_name="avaliacaoempresa",
            old_name="created_at",
            new_name="created",
        ),
        migrations.RenameField(
            model_name="avaliacaoempresa",
            old_name="updated_at",
            new_name="modified",
        ),
        migrations.AlterField(
            model_name="avaliacaoempresa",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True, verbose_name="created"
            ),
        ),
        migrations.AlterField(
            model_name="avaliacaoempresa",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(
                auto_now=True, verbose_name="modified"
            ),
        ),
    ]
