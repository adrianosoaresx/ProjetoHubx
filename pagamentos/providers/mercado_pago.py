from __future__ import annotations

import os
from typing import Any

import requests
from django.utils.translation import gettext_lazy as _

from pagamentos.exceptions import PagamentoInvalidoError, PagamentoProviderError
from pagamentos.models import Pedido, Transacao
from pagamentos.providers.base import PaymentProvider


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
        return self._request("GET", f"/v1/payments/{transacao.external_id}")

    def _build_pix_payload(self, pedido: Pedido, dados_pagamento: dict[str, Any]) -> dict[str, Any]:
        return {
            "transaction_amount": float(pedido.valor),
            "payment_method_id": "pix",
            "description": dados_pagamento.get("descricao") or "Pagamento Hubx",
            "payer": self._payer_data(dados_pagamento),
            "date_of_expiration": dados_pagamento.get("expiracao"),
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
        return {
            "transaction_amount": float(pedido.valor),
            "payment_method_id": "bolbradesco",
            "payer": self._payer_data(dados_pagamento),
            "date_of_expiration": vencimento,
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

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(
                method,
                url,
                headers=self._headers(),
                timeout=10,
                **kwargs,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - erro tratado abaixo
            raise PagamentoProviderError(str(exc)) from exc
        except requests.RequestException as exc:  # pragma: no cover - erro tratado abaixo
            raise PagamentoProviderError(str(exc)) from exc

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover
            raise PagamentoProviderError(_("Resposta inválida do provedor.")) from exc
