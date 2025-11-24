from __future__ import annotations

import base64
import logging
import os
from typing import Any

import requests
from django.utils.translation import gettext_lazy as _

from pagamentos.exceptions import PagamentoInvalidoError, PagamentoProviderError
from pagamentos.models import Pedido, Transacao
from pagamentos.providers.base import PaymentProvider

logger = logging.getLogger(__name__)


class PayPalProvider(PaymentProvider):
    """Integração básica com a API REST do PayPal."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        session: requests.Session | None = None,
        currency: str | None = None,
    ) -> None:
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("PAYPAL_CLIENT_SECRET", "")
        self.base_url = base_url or os.getenv("PAYPAL_API_URL", "https://api-m.sandbox.paypal.com")
        self.session = session or requests.Session()
        self._access_token: str | None = None
        self.currency = currency or os.getenv("PAYPAL_CURRENCY", "BRL")

    @classmethod
    def from_organizacao(cls, organizacao, **kwargs: Any) -> "PayPalProvider":
        if not organizacao:
            return cls(**kwargs)
        return cls(
            client_id=getattr(organizacao, "paypal_client_id", None),
            client_secret=getattr(organizacao, "paypal_client_secret", None),
            base_url=kwargs.get("base_url"),
            session=kwargs.get("session"),
            currency=getattr(organizacao, "paypal_currency", None),
        )

    def criar_cobranca(
        self, pedido: Pedido, metodo: str, dados_pagamento: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if metodo != Transacao.Metodo.PAYPAL:
            raise PagamentoInvalidoError(_("Método de pagamento não suportado pelo PayPal."))

        dados_pagamento = dados_pagamento or {}
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": str(pedido.pk),
                    "amount": {"currency_code": self.currency, "value": f"{pedido.valor:.2f}"},
                    "description": dados_pagamento.get("descricao") or "Pagamento Hubx",
                }
            ],
            "payer": self._payer_data(dados_pagamento),
        }

        logger.info(
            "paypal_criar_cobranca",
            extra={"pedido_id": pedido.id, "valor": float(pedido.valor), "currency": self.currency},
        )
        return self._post("/v2/checkout/orders", payload)

    def confirmar_pagamento(self, transacao: Transacao) -> dict[str, Any]:
        if not transacao.external_id:
            raise PagamentoInvalidoError(_("Transação sem identificador externo."))
        return self._request("GET", f"/v2/checkout/orders/{transacao.external_id}")

    def estornar_pagamento(self, transacao: Transacao) -> dict[str, Any]:
        capture_id = self._capture_id(transacao)
        if not capture_id:
            raise PagamentoInvalidoError(_("Transação sem captura registrada no PayPal."))
        return self._post(f"/v2/payments/captures/{capture_id}/refund", {})

    def consultar_pagamento(self, transacao: Transacao) -> dict[str, Any]:
        return self.confirmar_pagamento(transacao)

    def _capture_id(self, transacao: Transacao) -> str | None:
        payments = (transacao.detalhes or {}).get("purchase_units", [{}])[0].get("payments", {})
        captures = payments.get("captures") or []
        if captures:
            return captures[0].get("id")
        return None

    def _payer_data(self, dados_pagamento: dict[str, Any]) -> dict[str, Any]:
        email = dados_pagamento.get("email")
        if not email:
            raise PagamentoInvalidoError(_("E-mail do pagador é obrigatório para PayPal."))

        nome = (dados_pagamento.get("nome") or "").strip()
        partes = nome.split(" ", 1)
        given_name = partes[0] if partes else ""
        surname = partes[1] if len(partes) > 1 else ""
        return {
            "email_address": email,
            "name": {"given_name": given_name, "surname": surname},
        }

    def _headers(self) -> dict[str, str]:
        token = self._obter_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _obter_access_token(self) -> str:
        if not (self.client_id and self.client_secret):
            raise PagamentoProviderError(_("Credenciais do PayPal ausentes."))

        if self._access_token:
            return self._access_token

        token_url = f"{self.base_url}/v1/oauth2/token"
        try:
            response = self.session.post(
                token_url,
                data={"grant_type": "client_credentials"},
                headers={"Authorization": f"Basic {self._encode_credentials()}"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data.get("access_token", "")
        except requests.HTTPError as exc:  # pragma: no cover - erro tratado abaixo
            logger.warning(
                "paypal_http_error",
                extra={"url": token_url, "method": "POST", "status_code": getattr(exc.response, "status_code", None)},
            )
            raise PagamentoProviderError(str(exc)) from exc
        except requests.RequestException as exc:  # pragma: no cover - erro tratado abaixo
            logger.warning("paypal_request_error", extra={"url": token_url, "method": "POST"})
            raise PagamentoProviderError(str(exc)) from exc
        except ValueError as exc:  # pragma: no cover - resposta inválida
            raise PagamentoProviderError(_("Resposta inválida do PayPal.")) from exc

        if not self._access_token:
            raise PagamentoProviderError(_("Não foi possível obter o token de acesso do PayPal."))
        return self._access_token

    def _encode_credentials(self) -> str:
        credentials = f"{self.client_id}:{self.client_secret}".encode()
        return base64.b64encode(credentials).decode()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        try:
            response = self.session.request(
                method,
                url,
                headers={**self._headers(), **headers},
                timeout=10,
                **kwargs,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - erro tratado abaixo
            logger.warning(
                "paypal_http_error",
                extra={"url": url, "method": method, "status_code": getattr(exc.response, "status_code", None)},
            )
            raise PagamentoProviderError(str(exc)) from exc
        except requests.RequestException as exc:  # pragma: no cover - erro tratado abaixo
            logger.warning("paypal_request_error", extra={"url": url, "method": method})
            raise PagamentoProviderError(str(exc)) from exc

        try:
            data = response.json()
            logger.info(
                "paypal_resposta_sucesso",
                extra={"url": url, "method": method, "status_code": response.status_code},
            )
            return data
        except ValueError as exc:  # pragma: no cover
            raise PagamentoProviderError(_("Resposta inválida do provedor.")) from exc
