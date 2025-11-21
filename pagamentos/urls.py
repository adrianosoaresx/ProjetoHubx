from __future__ import annotations

from typing import List

from django.urls import URLPattern, path

from pagamentos.views import (
    CheckoutView,
    TransacaoCSVExportView,
    TransacaoRevisaoView,
    TransacaoStatusView,
    WebhookView,
)

urlpatterns: List[URLPattern] = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("checkout/status/<int:pk>/", TransacaoStatusView.as_view(), name="status"),
    path("webhook/mercadopago/", WebhookView.as_view(), name="webhook-mercadopago"),
    path("relatorios/transacoes/", TransacaoRevisaoView.as_view(), name="relatorios"),
    path("relatorios/transacoes.csv", TransacaoCSVExportView.as_view(), name="transacoes-csv"),
]
