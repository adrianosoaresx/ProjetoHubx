from __future__ import annotations

from typing import List

from django.urls import URLPattern, path

from pagamentos.views import (
    CheckoutView,
    MercadoPagoRetornoView,
    PayPalWebhookView,
    TransacaoCSVExportView,
    TransacaoRevisaoView,
    TransacaoStatusView,
    WebhookView,
)

urlpatterns: List[URLPattern] = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("checkout/status/<int:pk>/", TransacaoStatusView.as_view(), name="status"),
    path(
        "mp/retorno/<str:status>/",
        MercadoPagoRetornoView.as_view(),
        name="mercadopago-retorno",
    ),
    path("webhook/mercadopago/", WebhookView.as_view(), name="webhook-mercadopago"),
    path(
        "api/payments/mercadopago/webhook/",
        WebhookView.as_view(),
        name="webhook-mercadopago-api",
    ),
    path("webhook/paypal/", PayPalWebhookView.as_view(), name="webhook-paypal"),
    path("relatorios/transacoes/", TransacaoRevisaoView.as_view(), name="relatorios"),
    path("relatorios/transacoes.csv", TransacaoCSVExportView.as_view(), name="transacoes-csv"),
]
