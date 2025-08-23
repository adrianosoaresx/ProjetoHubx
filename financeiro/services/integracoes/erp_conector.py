"""Serviço de comunicação com ERPs externos."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

import requests

from financeiro.models import IntegracaoConfig, IntegracaoIdempotency, IntegracaoLog


class ERPConectorError(Exception):
    """Erro genérico ao se comunicar com o ERP."""


class ERPConector:
    """Cliente simples para integração com ERPs.

    Este serviço encapsula detalhes de autenticação, uso de ``Idempotency-Key``
    e registro de logs das requisições. A implementação foca em oferecer uma
    base para extensões futuras e é propositalmente minimalista.
    """

    def __init__(
        self,
        config: IntegracaoConfig,
        *,
        retries: int = 3,
        backoff: float = 1.0,
    ):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.session = requests.Session()
        self.retries = retries
        self.backoff = backoff
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
        timeout = kwargs.pop("timeout", 10)

        for attempt in range(1, self.retries + 1):
            start = time.monotonic()
            try:
                response = self.session.request(
                    method, url, headers=headers, timeout=timeout, **kwargs
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                duration = int((time.monotonic() - start) * 1000)
                status = (
                    "timeout" if isinstance(exc, requests.Timeout) else "connection_error"
                )
                IntegracaoLog.objects.create(
                    provedor=self.config.nome,
                    acao=f"{method} {path} (tentativa {attempt})",
                    payload_in=kwargs.get("json"),
                    payload_out={},
                    status=status,
                    duracao_ms=duration,
                    erro=str(exc),
                )
                if attempt == self.retries:
                    raise ERPConectorError("Erro ao comunicar com ERP") from exc
                time.sleep(self.backoff * attempt)
                continue

            duration = int((time.monotonic() - start) * 1000)
            IntegracaoLog.objects.create(
                provedor=self.config.nome,
                acao=f"{method} {path} (tentativa {attempt})",
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
