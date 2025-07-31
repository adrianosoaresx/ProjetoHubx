from __future__ import annotations

from typing import Any, Dict

from django.db.models import Model

from .models import Organizacao, OrganizacaoLog


def serialize_organizacao(org: Organizacao) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for field in org._meta.fields:
        name = field.name
        value = getattr(org, name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif hasattr(value, "name"):
            value = value.name
        data[name] = value
    return data


def registrar_log(
    organizacao: Organizacao,
    usuario: Model | None,
    acao: str,
    dados_antigos: Dict[str, Any],
    dados_novos: Dict[str, Any],
) -> None:
    OrganizacaoLog.objects.create(
        organizacao=organizacao,
        usuario=usuario,
        acao=acao,
        dados_antigos=dados_antigos,
        dados_novos=dados_novos,
    )
