"""Serviço de comunicação com ERPs externos."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

import requests

from financeiro.models import IntegracaoConfig, IntegracaoIdempotency, IntegracaoLog


class ERPConector:
    """Cliente simples para integração com ERPs.

    Este serviço encapsula detalhes de autenticação, uso de ``Idempotency-Key``
    e registro de logs das requisições. A implementação foca em oferecer uma
    base para extensões futuras e é propositalmente minimalista.
    """

    def __init__(self, config: IntegracaoConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.session = requests.Session()
        if config.credenciais_encrypted:
            self.session.headers["Authorization"] = f"Bearer {config.credenciais_encrypted}"

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------
    def listar_lancamentos_externos(self) -> Any:
        """Retorna lançamentos financeiros disponíveis no ERP."""
        response = self._request("GET", "/lancamentos/")
        return response.json()

    def enviar_lancamento(self, lancamento: Dict[str, Any]) -> Any:
        """Envia um lançamento financeiro para o ERP."""
        idem = self._registrar_idempotencia("lancamento")
        response = self._request(
            "POST", "/lancamentos/", json=lancamento, idempotency_key=idem
        )
        return response.json()

    def conciliar_pagamento(
        self, lancamento: Dict[str, Any], dados_externos: Dict[str, Any]
    ) -> Any:
        """Solicita conciliação de um pagamento."""
        idem = self._registrar_idempotencia("conciliacao")
        payload = {"lancamento": lancamento, "dados": dados_externos}
        response = self._request(
            "POST", "/conciliacao/", json=payload, idempotency_key=idem
        )
        return response.json()

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------
    def _registrar_idempotencia(self, recurso: str) -> str:
        """Cria registro de idempotência e retorna chave gerada."""
        key = str(uuid.uuid4())
        IntegracaoIdempotency.objects.create(
            idempotency_key=key, provedor=self.config.nome, recurso=recurso, status="pending"
        )
        return key

    def _request(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Executa a requisição HTTP registrando logs e erros."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        start = time.monotonic()
        response = self.session.request(method, url, headers=headers, **kwargs)
        duration = int((time.monotonic() - start) * 1000)
        IntegracaoLog.objects.create(
            provedor=self.config.nome,
            acao=f"{method} {path}",
            payload_in=kwargs.get("json"),
            payload_out=self._safe_json(response),
            status=str(response.status_code),
            duracao_ms=duration,
            erro="" if response.ok else response.text,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _safe_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text
