from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0014_rename_idx_lanc_centro_conta_status_venc_idx_lanc_cc_status_venc"),
        ("financeiro", "0014_rename_idx_lanc_centro_conta_status_venc_idx_lanc_cc_status_venc_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="lancamentofinanceiro",
            name="ajustado",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="lancamentofinanceiro",
            name="lancamento_original",
            field=models.ForeignKey(
                on_delete=models.SET_NULL,
                blank=True,
                null=True,
                related_name="ajustes",
                to="financeiro.lancamentofinanceiro",
            ),
        ),
    ]
