from __future__ import annotations

import hmac
import json
import logging
import os
from hashlib import sha256
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.views import APIView

from eventos.models import InscricaoEvento
from pagamentos.forms import CheckoutForm
from pagamentos.models import Pedido, Transacao
from pagamentos.providers import MercadoPagoProvider
from pagamentos.serializers import CheckoutResponseSerializer, CheckoutSerializer, WebhookSerializer
from pagamentos.services import PagamentoService

logger = logging.getLogger(__name__)


class CheckoutView(APIView):
    template_name = "pagamentos/checkout.html"
    permission_classes = [AllowAny]

    @extend_schema(
        methods=["GET"],
        responses=OpenApiResponse(description="Página de checkout com formulário HTMX"),
        tags=["Pagamentos"],
    )
    def get(self, request: HttpRequest) -> HttpResponse:
        provider = MercadoPagoProvider()
        form = CheckoutForm()
        return self._render_response(
            request,
            form=form,
            provider_public_key=provider.public_key,
        )

    @extend_schema(
        methods=["POST"],
        request=CheckoutSerializer,
        responses={201: CheckoutResponseSerializer},
        tags=["Pagamentos"],
        description=_("Inicia o pagamento no Mercado Pago e retorna a transação criada."),
    )
    def post(self, request: HttpRequest) -> HttpResponse:
        form = CheckoutForm(request.POST)
        provider = MercadoPagoProvider()
        if not form.is_valid():
            return self._render_response(
                request, form=form, provider_public_key=provider.public_key, status=400
            )

        pedido = Pedido.objects.create(
            valor=form.cleaned_data["valor"],
            email=form.cleaned_data.get("email"),
            nome=form.cleaned_data.get("nome"),
            documento=form.cleaned_data.get("documento"),
        )
        service = PagamentoService(provider)
        dados_pagamento = self._dados_pagamento(form.cleaned_data)
        transacao = service.iniciar_pagamento(pedido, form.cleaned_data["metodo"], dados_pagamento)
        contexto = {
            "form": form,
            "transacao": transacao,
            "mensagem": _("Pagamento iniciado com sucesso."),
            "provider_public_key": provider.public_key,
            "status": 201,
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


class TransacaoStatusView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Pagamentos"], responses=CheckoutResponseSerializer)
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        try:
            transacao = Transacao.objects.select_related("pedido").get(pk=pk)
        except Transacao.DoesNotExist:
            return HttpResponseBadRequest("invalid transaction")

        if transacao.status == Transacao.Status.PENDENTE:
            provider = MercadoPagoProvider()
            service = PagamentoService(provider)
            try:
                service.confirmar_pagamento(transacao)
                transacao.refresh_from_db()
            except Exception:
                logger.exception(
                    "polling_status_failed", extra={"transacao_id": transacao.id}
                )

        return render(
            request,
            "pagamentos/partials/checkout_resultado.html",
            {"transacao": transacao, "form": CheckoutForm()},
        )


@method_decorator(csrf_exempt, name="dispatch")
class WebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    provider_class = MercadoPagoProvider

    @extend_schema(
        methods=["POST"],
        request=WebhookSerializer,
        responses={200: OpenApiResponse(description="Webhook processado")},
        tags=["Pagamentos"],
        description=_("Webhook de notificações do Mercado Pago com verificação de assinatura."),
    )
    def post(self, request: HttpRequest) -> HttpResponse:
        if not self._assinatura_valida(request):
            logger.warning("webhook_assinatura_invalida")
            return HttpResponseForbidden()

        payload = self._parse_body(request.body)
        external_id = str(payload.get("data", {}).get("id") or payload.get("id", ""))
        if not external_id:
            logger.warning("webhook_sem_id")
            return HttpResponseBadRequest("missing id")

        try:
            transacao = Transacao.objects.select_related("pedido").get(external_id=external_id)
        except Transacao.DoesNotExist:
            logger.info("webhook_transacao_desconhecida", extra={"external_id": external_id})
            return HttpResponse(status=200)

        provider = self.provider_class()
        service = PagamentoService(provider)
        service.confirmar_pagamento(transacao)
        logger.info(
            "webhook_pagamento_confirmado",
            extra={"transacao_id": transacao.id, "external_id": external_id},
        )
        self._atualizar_inscricao(transacao)
        return HttpResponse(status=200)

    def _atualizar_inscricao(self, transacao: Transacao) -> None:
        try:
            inscricao = transacao.inscricao_evento
        except InscricaoEvento.DoesNotExist:
            return

        if transacao.status != Transacao.Status.APROVADA:
            return

        try:
            inscricao.pagamento_validado = True
            inscricao.transacao = transacao
            inscricao.confirmar_inscricao()
        except Exception:
            logger.exception(
                "webhook_inscricao_confirmacao_falhou",
                extra={"inscricao_id": inscricao.pk, "transacao_id": transacao.pk},
            )

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


class TransacaoRevisaoView(APIView):
    permission_classes = [IsAdminUser]
    template_name = "pagamentos/transacoes_revisao.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        status = request.GET.get("status") or "all"
        filtros = [Transacao.Status.PENDENTE, Transacao.Status.FALHOU]
        if status in Transacao.Status.values:
            filtros = [status]
        transacoes = Transacao.objects.select_related("pedido").filter(status__in=filtros).order_by(
            "-criado_em"
        )
        contexto = {
            "transacoes": transacoes,
            "status_filtro": status,
        }
        return render(request, self.template_name, contexto)


class TransacaoCSVExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request: HttpRequest) -> HttpResponse:
        qs = Transacao.objects.select_related("pedido").order_by("-criado_em")
        linhas = ["data,valor,status,metodo"]
        for transacao in qs:
            linhas.append(
                f"{transacao.criado_em.isoformat()},{transacao.valor},{transacao.status},{transacao.metodo}"
            )
        conteudo = "\n".join(linhas)
        response = HttpResponse(conteudo, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=transacoes.csv"
        return response
