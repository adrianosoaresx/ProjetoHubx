from __future__ import annotations

import hmac
import json
import os
from hashlib import sha256
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from pagamentos.forms import CheckoutForm
from pagamentos.models import Pedido, Transacao
from pagamentos.providers import MercadoPagoProvider
from pagamentos.services import PagamentoService


class CheckoutView(View):
    template_name = "pagamentos/checkout.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = CheckoutForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return self._render_response(request, form=form, status=400)

        pedido = Pedido.objects.create(valor=form.cleaned_data["valor"])
        provider = MercadoPagoProvider()
        service = PagamentoService(provider)
        dados_pagamento = self._dados_pagamento(form.cleaned_data)
        transacao = service.iniciar_pagamento(pedido, form.cleaned_data["metodo"], dados_pagamento)
        contexto = {
            "form": form,
            "transacao": transacao,
            "mensagem": _("Pagamento iniciado com sucesso."),
        }
        return self._render_response(request, **contexto)

    def _render_response(self, request: HttpRequest, **contexto: Any) -> HttpResponse:
        template = (
            "pagamentos/partials/checkout_resultado.html"
            if request.headers.get("HX-Request")
            else self.template_name
        )
        status = contexto.pop("status", 200)
        return render(request, template, contexto, status=status)

    def _dados_pagamento(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "email": cleaned_data["email"],
            "nome": cleaned_data["nome"],
            "document_number": cleaned_data["documento"],
            "token": cleaned_data.get("token_cartao"),
            "parcelas": cleaned_data.get("parcelas"),
            "vencimento": cleaned_data.get("vencimento"),
        }


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(View):
    provider_class = MercadoPagoProvider

    def post(self, request: HttpRequest) -> HttpResponse:
        if not self._assinatura_valida(request):
            return HttpResponseForbidden()

        payload = self._parse_body(request.body)
        external_id = str(payload.get("data", {}).get("id") or payload.get("id", ""))
        if not external_id:
            return HttpResponseBadRequest("missing id")

        try:
            transacao = Transacao.objects.select_related("pedido").get(external_id=external_id)
        except Transacao.DoesNotExist:
            return HttpResponse(status=200)

        provider = self.provider_class()
        service = PagamentoService(provider)
        service.confirmar_pagamento(transacao)
        return HttpResponse(status=200)

    def _parse_body(self, raw_body: bytes) -> dict[str, Any]:
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _assinatura_valida(self, request: HttpRequest) -> bool:
        secret = os.getenv("MERCADO_PAGO_WEBHOOK_SECRET")
        if not secret:
            return True
        assinatura = request.headers.get("X-Signature")
        if not assinatura:
            return False
        calculada = hmac.new(secret.encode(), msg=request.body, digestmod=sha256).hexdigest()
        return hmac.compare_digest(assinatura, calculada)
