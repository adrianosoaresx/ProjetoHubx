from __future__ import annotations

from typing import List

from django.urls import URLPattern, path

from pagamentos.views import CheckoutView, WebhookView

urlpatterns: List[URLPattern] = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("webhook/mercadopago/", WebhookView.as_view(), name="webhook-mercadopago"),
]
