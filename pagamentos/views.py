from __future__ import annotations

import hmac
import json
import logging
import os
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.views import APIView

from eventos.models import InscricaoEvento
from organizacoes.models import Organizacao
from pagamentos.forms import CheckoutForm
from pagamentos.models import Pedido, Transacao
from pagamentos.providers import MercadoPagoProvider, PayPalProvider, PaymentProvider
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
        organizacao = self._obter_organizacao(request)
        provider = MercadoPagoProvider.from_organizacao(organizacao)
        form = CheckoutForm(organizacao=organizacao)
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
        description=_("Inicia o pagamento no provedor selecionado e retorna a transação criada."),
    )
    def post(self, request: HttpRequest) -> HttpResponse:
        organizacao = self._obter_organizacao(request)
        form = CheckoutForm(request.POST, user=request.user, organizacao=organizacao)
        if not form.is_valid():
            return self._render_response(
                request,
                form=form,
                provider_public_key=MercadoPagoProvider.from_organizacao(organizacao).public_key,
                status=400,
            )

        organizacao = self._obter_organizacao(request, str(form.cleaned_data.get("organizacao_id") or ""))
        provider = self._provider_for_method(form.cleaned_data.get("metodo"), organizacao)

        pedido = Pedido.objects.create(
            valor=form.cleaned_data["valor"],
            email=form.cleaned_data.get("email"),
            nome=form.cleaned_data.get("nome"),
            documento=form.cleaned_data.get("documento"),
            organizacao=organizacao,
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

    def _provider_for_method(self, metodo: str | None, organizacao: Organizacao | None = None) -> PaymentProvider:
        if metodo == Transacao.Metodo.PAYPAL:
            return PayPalProvider.from_organizacao(organizacao)
        return MercadoPagoProvider.from_organizacao(organizacao)

    def _obter_organizacao(
        self, request: HttpRequest, organizacao_id: str | None = None
    ) -> Organizacao | None:
        raw_id = organizacao_id or request.POST.get("organizacao_id") or request.GET.get("organizacao_id")
        if raw_id:
            try:
                org = Organizacao.objects.filter(id=raw_id).first()
                if org:
                    return org
            except (ValueError, TypeError):
                pass

        host = (request.get_host() or "").split(":")[0].lower()
        if host:
            subdomain = host.split(".")[0]
            org = (
                Organizacao.objects.filter(
                    Q(nome_site__iexact=subdomain)
                    | Q(nome_site__iexact=host)
                    | Q(site__icontains=host)
                ).first()
            )
            if org:
                return org

            for candidate in Organizacao.objects.exclude(site="").iterator():
                netloc = urlparse(candidate.site).netloc.lower()
                if netloc and (host == netloc or host.endswith(netloc)):
                    return candidate
        return None

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
            "payment_method_id": cleaned_data.get("payment_method_id"),
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
            provider = self._provider_for_transacao(transacao)
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

    def _provider_for_transacao(self, transacao: Transacao) -> PaymentProvider:
        if transacao.metodo == Transacao.Metodo.PAYPAL:
            return PayPalProvider.from_organizacao(getattr(transacao.pedido, "organizacao", None))
        return MercadoPagoProvider.from_organizacao(getattr(transacao.pedido, "organizacao", None))


class MercadoPagoRetornoView(APIView):
    permission_classes = [AllowAny]
    template_name = "pagamentos/retorno.html"

    def get(self, request: HttpRequest, status: str) -> HttpResponse:
        retorno_status = status.lower()
        if retorno_status not in {"sucesso", "falha", "pendente"}:
            return HttpResponseBadRequest("invalid status")

        transacao = self._buscar_transacao(request)
        organizacao = getattr(getattr(transacao, "pedido", None), "organizacao", None)
        if transacao:
            provider = MercadoPagoProvider.from_organizacao(organizacao)
            service = PagamentoService(provider)
            try:
                service.confirmar_pagamento(transacao)
                transacao.refresh_from_db()
            except Exception:
                logger.exception(
                    "retorno_mp_confirmacao_falhou",
                    extra={"transacao_id": transacao.id, "external_id": transacao.external_id},
                )

        contexto = {
            "mensagem": self._mensagem(retorno_status, transacao is not None),
            "transacao": transacao,
            "form": CheckoutForm(organizacao=organizacao),
            "retorno_status": retorno_status,
        }
        return render(request, self.template_name, contexto)

    def _buscar_transacao(self, request: HttpRequest) -> Transacao | None:
        payment_id = (
            request.GET.get("payment_id")
            or request.GET.get("collection_id")
            or request.GET.get("id")
        )
        external_reference = request.GET.get("external_reference")

        queryset = Transacao.objects.select_related("pedido", "pedido__organizacao")
        if payment_id:
            transacao = queryset.filter(external_id=str(payment_id)).first()
            if transacao:
                return transacao
        if external_reference:
            return queryset.filter(external_id=str(external_reference)).first()
        return None

    def _mensagem(self, status: str, possui_transacao: bool) -> str:
        if not possui_transacao:
            return _("Não localizamos a transação informada. Verifique os dados ou tente novamente.")
        if status == "sucesso":
            return _("Pagamento confirmado. Estamos validando seus dados.")
        if status == "falha":
            return _("Pagamento não foi concluído. Você pode tentar novamente ou escolher outro método.")
        return _("Pagamento em análise. Assim que houver atualização, atualizaremos este status.")


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
        payload = self._parse_body(request.body)
        external_id = str(
            payload.get("data", {}).get("id")
            or payload.get("id", "")
            or payload.get("resource", {}).get("id", "")
        )
        if not external_id:
            logger.warning("webhook_sem_id")
            return HttpResponseBadRequest("missing id")

        transacao = None
        try:
            transacao = (
                Transacao.objects.select_related("pedido", "pedido__organizacao")
                .get(external_id=external_id)
            )
        except Transacao.DoesNotExist:
            logger.info("webhook_transacao_desconhecida", extra={"external_id": external_id})
        organizacao = self._organizacao_from_request(request, payload, transacao)

        if not self._assinatura_valida(request, organizacao):
            logger.warning("webhook_assinatura_invalida")
            return HttpResponseForbidden()

        if not transacao:
            return HttpResponse(status=200)

        provider = (
            self.provider_class.from_organizacao(organizacao)
            if hasattr(self.provider_class, "from_organizacao")
            else self.provider_class()
        )
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

    def _assinatura_valida(
        self, request: HttpRequest, organizacao: Organizacao | None
    ) -> bool:
        secret = (organizacao.mercado_pago_webhook_secret if organizacao else None) or os.getenv(
            "MERCADO_PAGO_WEBHOOK_SECRET"
        )
        if not secret:
            return True
        assinatura = request.headers.get("X-Signature")
        if not assinatura:
            return False
        calculada = hmac.new(secret.encode(), msg=request.body, digestmod=sha256).hexdigest()
        return hmac.compare_digest(assinatura, calculada)

    def _organizacao_from_request(
        self, request: HttpRequest, payload: dict[str, Any], transacao: Transacao | None
    ) -> Organizacao | None:
        if transacao and getattr(transacao.pedido, "organizacao_id", None):
            return transacao.pedido.organizacao

        host = (request.get_host() or "").split(":")[0].lower()
        if host:
            subdomain = host.split(".")[0]
            org = (
                Organizacao.objects.filter(
                    Q(nome_site__iexact=subdomain)
                    | Q(nome_site__iexact=host)
                    | Q(site__icontains=host)
                ).first()
            )
            if org:
                return org

            for candidate in Organizacao.objects.exclude(site="").iterator():
                netloc = urlparse(candidate.site).netloc.lower()
                if netloc and (host == netloc or host.endswith(netloc)):
                    return candidate
        return None


class PayPalWebhookView(WebhookView):
    provider_class = PayPalProvider

    def _assinatura_valida(self, request: HttpRequest, organizacao: Organizacao | None) -> bool:
        secret = (organizacao.paypal_webhook_secret if organizacao else None) or os.getenv(
            "PAYPAL_WEBHOOK_SECRET"
        )
        if not secret:
            return True
        assinatura = request.headers.get("X-Paypal-Signature")
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
