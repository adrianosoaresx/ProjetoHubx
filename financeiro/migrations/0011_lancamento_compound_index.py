from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0010_soft_delete_and_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="lancamentofinanceiro",
            index=models.Index(
                fields=["centro_custo", "conta_associado", "status", "data_vencimento"],
                name="idx_lanc_centro_conta_status_venc",
            ),
        ),
    ]

