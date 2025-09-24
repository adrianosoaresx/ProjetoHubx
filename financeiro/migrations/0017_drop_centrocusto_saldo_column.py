from __future__ import annotations

from django.db import migrations, models


def drop_centrocusto_saldo(apps, schema_editor):
    centro_model = apps.get_model("financeiro", "CentroCusto")
    table = centro_model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, table)
        }
    if "saldo" not in existing_columns:
        return
    field = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    field.set_attributes_from_name("saldo")
    schema_editor.remove_field(centro_model, field)


def restore_centrocusto_saldo(apps, schema_editor):
    centro_model = apps.get_model("financeiro", "CentroCusto")
    table = centro_model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, table)
        }
    if "saldo" in existing_columns:
        return
    field = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    field.set_attributes_from_name("saldo")
    schema_editor.add_field(centro_model, field)


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0016_merge_20250924_1407"),
    ]

    operations = [
        migrations.RunPython(drop_centrocusto_saldo, restore_centrocusto_saldo),
    ]
