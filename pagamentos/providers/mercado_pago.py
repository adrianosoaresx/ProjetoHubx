from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone as dt_timezone
from typing import Any

import requests
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from pagamentos.exceptions import PagamentoInvalidoError, PagamentoProviderError
from pagamentos.models import Pedido, Transacao
from pagamentos.providers.base import PaymentProvider

logger = logging.getLogger(__name__)

# Compatibilidade com Python < 3.11, que não possui datetime.UTC
UTC = dt_timezone.utc


class MercadoPagoProvider(PaymentProvider):
    """Integração direta com o Mercado Pago via API HTTP."""

    def __init__(
        self,
        access_token: str | None = None,
        public_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.access_token = access_token or os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "")
        self.public_key = public_key or os.getenv("MERCADO_PAGO_PUBLIC_KEY", "")
        self.base_url = base_url or os.getenv("MERCADO_PAGO_API_URL", "https://api.mercadopago.com")
        self.session = session or requests.Session()

    @classmethod
    def from_organizacao(cls, organizacao, **kwargs: Any) -> "MercadoPagoProvider":
        if not organizacao:
            return cls(**kwargs)
        return cls(
            access_token=getattr(organizacao, "mercado_pago_access_token", None),
            public_key=getattr(organizacao, "mercado_pago_public_key", None),
            base_url=kwargs.get("base_url"),
            session=kwargs.get("session"),
        )

    def criar_cobranca(
        self, pedido: Pedido, metodo: str, dados_pagamento: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if not self.access_token:
            raise PagamentoProviderError(_("Token de acesso do Mercado Pago ausente."))

        dados_pagamento = dados_pagamento or {}
        if metodo == Transacao.Metodo.PIX:
            payload = self._build_pix_payload(pedido, dados_pagamento)
        elif metodo == Transacao.Metodo.CARTAO:
            payload = self._build_cartao_payload(pedido, dados_pagamento)
        elif metodo == Transacao.Metodo.BOLETO:
            payload = self._build_boleto_payload(pedido, dados_pagamento)
        else:
            raise PagamentoInvalidoError(_("Método de pagamento não suportado."))

        logger.info(
            "mercadopago_criar_cobranca",
            extra={
                "pedido_id": pedido.id,
                "metodo": metodo,
                "valor": float(pedido.valor),
                "payload_keys": sorted(payload.keys()),
            },
        )
        return self._post("/v1/payments", payload)

    def confirmar_pagamento(self, transacao: Transacao) -> dict[str, Any]:
        resposta = self.consultar_pagamento(transacao)
        return resposta

    def estornar_pagamento(self, transacao: Transacao) -> dict[str, Any]:
        if not transacao.external_id:
            raise PagamentoInvalidoError(_("Transação sem identificador externo."))
        return self._post(f"/v1/payments/{transacao.external_id}/refunds", {})

    def consultar_pagamento(self, transacao: Transacao) -> dict[str, Any]:
        if not transacao.external_id:
            raise PagamentoInvalidoError(_("Transação sem identificador externo."))
        resposta = self._request("GET", f"/v1/payments/{transacao.external_id}")
        logger.info(
            "mercadopago_consultar_pagamento",
            extra={"external_id": transacao.external_id, "status": resposta.get("status")},
        )
        return resposta

    def _build_pix_payload(self, pedido: Pedido, dados_pagamento: dict[str, Any]) -> dict[str, Any]:
        expiracao = self._format_datetime(dados_pagamento.get("expiracao"))
        return {
            "transaction_amount": float(pedido.valor),
            "payment_method_id": "pix",
            "description": dados_pagamento.get("descricao") or "Pagamento Hubx",
            "payer": self._payer_data(dados_pagamento),
            "date_of_expiration": expiracao,
        }

    def _build_cartao_payload(self, pedido: Pedido, dados_pagamento: dict[str, Any]) -> dict[str, Any]:
        token = dados_pagamento.get("token")
        if not token:
            raise PagamentoInvalidoError(_("Token do cartão não informado."))
        parcelas = int(dados_pagamento.get("parcelas", 1))
        return {
            "transaction_amount": float(pedido.valor),
            "token": token,
            "installments": parcelas,
            "payment_method_id": dados_pagamento.get("payment_method_id", "visa"),
            "payer": self._payer_data(dados_pagamento),
        }

    def _build_boleto_payload(self, pedido: Pedido, dados_pagamento: dict[str, Any]) -> dict[str, Any]:
        vencimento = dados_pagamento.get("vencimento")
        if not vencimento:
            raise PagamentoInvalidoError(_("Data de vencimento obrigatória para boleto."))
        if vencimento <= timezone.now():
            raise PagamentoInvalidoError(_("Boleto expirado ou com vencimento inválido."))
        vencimento_formatado = self._format_datetime(vencimento)
        return {
            "transaction_amount": float(pedido.valor),
            "payment_method_id": "bolbradesco",
            "payer": self._payer_data(dados_pagamento),
            "date_of_expiration": vencimento_formatado,
        }

    def _payer_data(self, dados_pagamento: dict[str, Any]) -> dict[str, Any]:
        email = dados_pagamento.get("email")
        if not email:
            raise PagamentoInvalidoError(_("E-mail do pagador é obrigatório."))
        return {
            "email": email,
            "first_name": dados_pagamento.get("first_name") or dados_pagamento.get("nome"),
            "last_name": dados_pagamento.get("last_name"),
            "identification": {
                "type": dados_pagamento.get("document_type", "CPF"),
                "number": dados_pagamento.get("document_number"),
            },
        }

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            path,
            json=payload,
            idempotency_key=self._generate_idempotency_key(),
        )

    def _request(
        self, method: str, path: str, idempotency_key: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method,
                url,
                headers=self._headers(idempotency_key=idempotency_key),
                timeout=10,
                **kwargs,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - erro tratado abaixo
            status_code = getattr(exc.response, "status_code", None)
            error_body: Any | None = None
            if exc.response is not None:
                try:
                    error_body = exc.response.json()
                except ValueError:
                    error_body = exc.response.text

            logger.warning(
                "mercadopago_http_error",
                extra={
                    "url": url,
                    "method": method,
                    "status_code": status_code,
                    "error_body": error_body,
                },
            )

            message = str(exc)
            if error_body:
                message = f"{message}: {error_body}"

            raise PagamentoProviderError(message) from exc
        except requests.RequestException as exc:  # pragma: no cover - erro tratado abaixo
            logger.warning(
                "mercadopago_request_error",
                extra={"url": url, "method": method},
            )
            raise PagamentoProviderError(str(exc)) from exc

        try:
            data = response.json()
            logger.info(
                "mercadopago_resposta_sucesso",
                extra={"url": url, "method": method, "status_code": response.status_code},
            )
            return data
        except ValueError as exc:  # pragma: no cover
            raise PagamentoProviderError(_("Resposta inválida do provedor.")) from exc

    @staticmethod
    def _generate_idempotency_key() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _format_datetime(value: Any) -> Any:
        """Converte objetos datetime para ISO 8601 para envio na API."""
        if value is None:
            return value

        dt: datetime | None = None

        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00").replace("UTC", "+00:00")
            for fmt in (
                "%d-%m-%YT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S%z",
            ):
                try:
                    dt = datetime.strptime(normalized, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                try:
                    dt = datetime.fromisoformat(normalized)
                except ValueError:
                    return value
        elif hasattr(value, "isoformat"):
            dt = value
        else:
            return value

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone=UTC)
        else:
            dt = dt.astimezone(UTC)

        return dt.isoformat(timespec="seconds")
