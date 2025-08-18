from __future__ import annotations

import os
from typing import Tuple

import requests


class CNPJServiceError(Exception):
    """Erro ao consultar serviço externo de CNPJ."""


def validate_cnpj_externo(cnpj: str, timeout: int | None = None) -> Tuple[bool, str]:
    base_url = os.getenv("CNPJ_VALIDATION_URL", "https://brasilapi.com.br/api/cnpj/v1/")
    if timeout is None:
        timeout = int(os.getenv("CNPJ_VALIDATION_TIMEOUT", "5"))
    try:
        resp = requests.get(f"{base_url}{cnpj}", timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:  # pragma: no cover - rede externa
        raise CNPJServiceError(str(exc)) from exc
    if data.get("cnpj"):
        return True, "brasilapi"
    return False, "brasilapi"
