from __future__ import annotations

from django.db import migrations


def create_indexes(apps, schema_editor) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        CREATE INDEX IF NOT EXISTS discussao_topico_search_idx
        ON discussao_topicodiscussao USING GIN (to_tsvector('portuguese', titulo || ' ' || conteudo));
        """
    )
    schema_editor.execute(
        """
        CREATE INDEX IF NOT EXISTS discussao_resposta_search_idx
        ON discussao_respostadiscussao USING GIN (to_tsvector('portuguese', conteudo));
        """
    )


def drop_indexes(apps, schema_editor) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS discussao_topico_search_idx;")
    schema_editor.execute("DROP INDEX IF EXISTS discussao_resposta_search_idx;")


class Migration(migrations.Migration):
    dependencies = [
        ("discussao", "0009_tag_deleted_tag_deleted_at"),
    ]

    operations = [migrations.RunPython(create_indexes, reverse_code=drop_indexes)]
