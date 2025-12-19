from __future__ import annotations

import hmac
import json
import logging
import os
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

import time

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.db import OperationalError
from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import OpenApiResponse, extend_schema
from payments import PaymentStatus, get_payment_model
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.views import APIView

from eventos.models import InscricaoEvento
from organizacoes.models import Organizacao
from pagamentos.forms import CheckoutForm
from pagamentos.exceptions import PagamentoProviderError
from pagamentos.models import Pedido, Transacao
from pagamentos.providers import MercadoPagoProvider, PayPalProvider
from pagamentos.serializers import CheckoutResponseSerializer, CheckoutSerializer, WebhookSerializer
from pagamentos.services import PagamentoService

logger = logging.getLogger(__name__)


def _mapear_status_pagamento(status: str) -> str:
    if status == PaymentStatus.CONFIRMED:
        return Transacao.Status.APROVADA
    if status == PaymentStatus.REFUNDED:
        return Transacao.Status.ESTORNADA
    if status in {PaymentStatus.REJECTED, PaymentStatus.ERROR}:
        return Transacao.Status.FALHOU
    return Transacao.Status.PENDENTE


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
        form = CheckoutForm(organizacao=organizacao)
        provider = MercadoPagoProvider.from_organizacao(organizacao)
        return self._render_response(
            request, form=form, provider_public_key=provider.public_key
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
            logger.warning("checkout_form_invalido", extra={"errors": form.errors.as_json()})
            provider = MercadoPagoProvider.from_organizacao(organizacao)
            return self._render_response(
                request, form=form, status=400, provider_public_key=provider.public_key
            )

        modo_exibicao = form.cleaned_data.get("modo_exibicao") or "pix"
        if modo_exibicao == "faturamento":
            inscricao = self._registrar_faturamento_inscricao(
                request,
                inscricao_uuid=form.cleaned_data.get("inscricao_uuid"),
                faturamento=form.cleaned_data.get("faturamento"),
                valor=form.cleaned_data["valor"],
            )
            if not inscricao:
                form.add_error(None, _("Não foi possível localizar a inscrição para faturamento."))
                return self._render_response(request, form=form, status=400)
            resultado_url = reverse("eventos:inscricao_resultado", kwargs={"uuid": inscricao.uuid})
            if request.headers.get("HX-Request"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = resultado_url
                return response
            return redirect(resultado_url)

        organizacao = self._obter_organizacao(
            request, str(form.cleaned_data.get("organizacao_id") or "")
        )
        pedido = Pedido.objects.create(
            valor=form.cleaned_data["valor"],
            email=form.cleaned_data.get("email"),
            nome=form.cleaned_data.get("nome"),
            organizacao=organizacao,
        )

        metodo_pagamento = form.cleaned_data.get("metodo")
        dados_pagamento = {
            "email": form.cleaned_data.get("email"),
            "nome": form.cleaned_data.get("nome"),
            "descricao": form.cleaned_data.get("descricao") or _("Pagamento Hubx"),
            "document_number": form.cleaned_data.get("documento"),
            "document_type": "CPF",
            "cep": form.cleaned_data.get("cep"),
            "logradouro": form.cleaned_data.get("logradouro"),
            "numero": form.cleaned_data.get("numero"),
            "bairro": form.cleaned_data.get("bairro"),
            "cidade": form.cleaned_data.get("cidade"),
            "estado": form.cleaned_data.get("estado"),
        }

        if metodo_pagamento == Transacao.Metodo.CARTAO:
            dados_pagamento.update(
                {
                    "token": form.cleaned_data.get("token_cartao"),
                    "payment_method_id": form.cleaned_data.get("payment_method_id"),
                    "parcelas": form.cleaned_data.get("parcelas") or 1,
                }
            )
        elif metodo_pagamento == Transacao.Metodo.BOLETO:
            dados_pagamento.update({"vencimento": form.cleaned_data.get("vencimento")})
        elif metodo_pagamento == Transacao.Metodo.PIX:
            dados_pagamento.update(
                {
                    "descricao": form.cleaned_data.get("pix_descricao")
                    or form.cleaned_data.get("descricao")
                    or _("Pagamento Hubx"),
                    "expiracao": form.cleaned_data.get("pix_expiracao"),
                }
            )

        provider = MercadoPagoProvider.from_organizacao(organizacao)
        service = PagamentoService(provider)
        redirect_url: str | None = None
        try:
            transacao = service.iniciar_pagamento(pedido, metodo_pagamento, dados_pagamento)
            redirect_url = (transacao.detalhes or {}).get("redirect_url")
            self._vincular_transacao_inscricao(request, transacao)
        except PagamentoProviderError as exc:
            form.add_error(None, str(exc))
            return self._render_response(request, form=form, status=400)
        except Exception:
            logger.exception(
                "erro_checkout_pagamento",
                extra={"pedido_id": pedido.id, "metodo": metodo_pagamento},
            )
            raise

        contexto = {
            "form": form,
            "transacao": transacao,
            "redirect_url": redirect_url,
            "mensagem": _("Pagamento iniciado com sucesso."),
            "status": 201,
        }
        if redirect_url:
            return redirect(redirect_url)
        return self._render_response(request, **contexto)

    def _registrar_faturamento_inscricao(
        self,
        request: HttpRequest,
        inscricao_uuid: str | None,
        faturamento: str | None,
        valor: Any,
    ) -> InscricaoEvento | None:
        if not faturamento:
            return None
        inscricao_uuid = (inscricao_uuid or "").strip()
        if not inscricao_uuid or not request.user.is_authenticated:
            return None
        try:
            inscricao = InscricaoEvento.objects.select_related("user").get(
                uuid=inscricao_uuid
            )
        except InscricaoEvento.DoesNotExist:
            logger.warning("checkout_inscricao_nao_encontrada", extra={"uuid": inscricao_uuid})
            return None
        if inscricao.user != request.user:
            logger.warning(
                "checkout_inscricao_usuario_invalido",
                extra={"uuid": inscricao_uuid, "user_id": request.user.id},
            )
            return None

        inscricao.metodo_pagamento = faturamento
        inscricao.valor_pago = valor
        inscricao.pagamento_validado = False
        inscricao.save(
            update_fields=[
                "metodo_pagamento",
                "valor_pago",
                "pagamento_validado",
                "updated_at",
            ]
        )
        return inscricao

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

    def _vincular_transacao_inscricao(
        self, request: HttpRequest, transacao: Transacao
    ) -> None:
        inscricao_uuid = (request.POST.get("inscricao_uuid") or "").strip()
        if not inscricao_uuid or not request.user.is_authenticated:
            return
        try:
            inscricao = InscricaoEvento.objects.select_related("user").get(
                uuid=inscricao_uuid
            )
        except InscricaoEvento.DoesNotExist:
            logger.warning("checkout_inscricao_nao_encontrada", extra={"uuid": inscricao_uuid})
            return
        if inscricao.user != request.user:
            logger.warning(
                "checkout_inscricao_usuario_invalido",
                extra={"uuid": inscricao_uuid, "user_id": request.user.id},
            )
            return

        inscricao.transacao = transacao
        inscricao.metodo_pagamento = transacao.metodo
        inscricao.pagamento_validado = transacao.status == Transacao.Status.APROVADA
        inscricao.save(
            update_fields=["transacao", "metodo_pagamento", "pagamento_validado", "updated_at"]
        )

    def _render_response(self, request: HttpRequest, **contexto: Any) -> HttpResponse:
        if "form" not in contexto:
            contexto["form"] = CheckoutForm()
        template = (
            "pagamentos/partials/checkout_resultado.html"
            if request.headers.get("HX-Request")
            else self.template_name
        )
        status = contexto.pop("status", 200)
        return render(request, template, contexto, status=status)


class ConfirmarPagamentoMixin:
    confirm_retry_delays = (0.0, 0.25, 0.5, 1.0)

    def _confirmar_pagamento_com_retry(
        self, service: PagamentoService, transacao: Transacao
    ) -> None:
        last_error: Exception | None = None
        for tentativa, delay in enumerate(self.confirm_retry_delays, start=1):
            if delay:
                time.sleep(delay)
            try:
                service.confirmar_pagamento(transacao)
                return
            except OperationalError as exc:
                last_error = exc
                logger.warning(
                    "confirmar_pagamento_operational_error",
                    extra={"transacao_id": transacao.id, "tentativa": tentativa},
                )
        if last_error:
            raise last_error

    def _sincronizar_pagamento_model(self, transacao: Transacao) -> None:
        payment_id = (transacao.detalhes or {}).get("payment_id")
        if not payment_id:
            return
        PaymentModel = get_payment_model()
        pagamento = PaymentModel.objects.filter(pk=payment_id).first()
        if not pagamento:
            return

        status_mapeado = _mapear_status_pagamento(pagamento.status)
        atualizacoes = []
        if transacao.status != status_mapeado:
            transacao.status = status_mapeado
            atualizacoes.append("status")
        if pagamento.transaction_id and transacao.external_id != pagamento.transaction_id:
            transacao.external_id = pagamento.transaction_id
            atualizacoes.append("external_id")
        detalhes = transacao.detalhes or {}
        detalhes.update({"payment_status": pagamento.status, "payment_token": pagamento.token})
        transacao.detalhes = detalhes
        atualizacoes.append("detalhes")
        if atualizacoes:
            transacao.save(update_fields=list(dict.fromkeys([*atualizacoes, "atualizado_em"])))


class TransacaoStatusView(ConfirmarPagamentoMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Pagamentos"], responses=CheckoutResponseSerializer)
    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        try:
            transacao = Transacao.objects.select_related("pedido").get(pk=pk)
        except Transacao.DoesNotExist:
            return HttpResponseBadRequest("invalid transaction")

        if transacao.status == Transacao.Status.PENDENTE:
            self._sincronizar_pagamento_model(transacao)

        if transacao.status == Transacao.Status.APROVADA:
            try:
                inscricao = transacao.inscricao_evento
            except InscricaoEvento.DoesNotExist:
                inscricao = None
            if inscricao:
                resultado_url = reverse(
                    "eventos:inscricao_resultado", kwargs={"uuid": inscricao.uuid}
                )
                if request.headers.get("HX-Request"):
                    response = HttpResponse(status=204)
                    response["HX-Redirect"] = resultado_url
                    return response
                contexto = self._montar_contexto_inscricao_resultado(request, inscricao)
                return render(request, "eventos/inscricoes/resultado.html", contexto)

        return render(
            request,
            "pagamentos/partials/checkout_resultado.html",
            {"transacao": transacao, "form": CheckoutForm()},
        )

    @staticmethod
    def _montar_contexto_inscricao_resultado(
        request: HttpRequest, inscricao: InscricaoEvento
    ) -> dict[str, Any]:
        evento = inscricao.evento
        share_url = request.build_absolute_uri(evento.get_absolute_url())
        inscricao_url = reverse("eventos:inscricao_overview", args=[evento.pk])
        convite = evento.convites.first()
        return {
            "evento": evento,
            "inscricao": inscricao,
            "status": "success",
            "message": None,
            "share_url": share_url,
            "inscricao_url": inscricao_url,
            "convite": convite,
            "title": _("Status da inscrição"),
        }


class MercadoPagoRetornoView(ConfirmarPagamentoMixin, APIView):
    permission_classes = [AllowAny]
    template_name = "pagamentos/retorno.html"

    def get(self, request: HttpRequest, status: str) -> HttpResponse:
        retorno_status = status.lower()
        if retorno_status not in {"sucesso", "falha", "pendente"}:
            return HttpResponseBadRequest("invalid status")

        transacao = self._buscar_transacao(request)
        if transacao:
            self._sincronizar_pagamento_model(transacao)
        organizacao = getattr(getattr(transacao, "pedido", None), "organizacao", None)

        contexto = {
            "mensagem": self._mensagem(retorno_status, transacao is not None),
            "transacao": transacao,
            "form": CheckoutForm(organizacao=organizacao),
            "retorno_status": retorno_status,
        }
        return render(request, self.template_name, contexto)

    def _buscar_transacao(self, request: HttpRequest) -> Transacao | None:
        payment_token = request.GET.get("token") or request.GET.get("external_reference")
        payment_id = (
            request.GET.get("payment_id")
            or request.GET.get("collection_id")
            or request.GET.get("id")
        )

        queryset = Transacao.objects.select_related("pedido", "pedido__organizacao")
        if payment_token:
            transacao = queryset.filter(external_id=str(payment_token)).first()
            if transacao:
                return transacao
            transacao = queryset.filter(detalhes__payment_token=str(payment_token)).first()
            if transacao:
                return transacao
        if payment_id:
            return queryset.filter(external_id=str(payment_id)).first()
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
class WebhookView(ConfirmarPagamentoMixin, APIView):
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
        self._confirmar_pagamento_com_retry(service, transacao)
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
