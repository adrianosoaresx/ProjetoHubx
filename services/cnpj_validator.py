import requests
from typing import Tuple


class CNPJValidationError(Exception):
    """Erro ao validar CNPJ"""


def validar_cnpj(cnpj: str, timeout: int = 5) -> Tuple[bool, str]:
    """Valida um CNPJ utilizando o serviço BrasilAPI.

    Retorna uma tupla ``(valido, fonte)`` indicando se o CNPJ foi
    validado com sucesso e qual foi a fonte utilizada. Nenhum dado
    sensível da API externa é retornado ou logado.
    """

    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:  # pragma: no cover - rede externa
        raise CNPJValidationError(str(exc)) from exc

    if data.get("cnpj"):
        # Consideramos válido apenas se o campo CNPJ existir no retorno
        return True, "brasilapi"
    return False, ""
