from __future__ import annotations

from typing import Any, Dict
import uuid
import json

from django.db.models import Model

from .models import Organizacao, OrganizacaoAtividadeLog


def serialize_organizacao(org: Organizacao) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for field in org._meta.fields:
        name = field.name
        value = getattr(org, name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, Model):
            value = value.pk
        elif hasattr(value, "name"):
            value = value.name
        data[name] = value
    return data


def registrar_log(
    organizacao: Organizacao,
    usuario: Model | None,
    acao: str,
    dados_anteriores: Dict[str, Any] | None = None,
    dados_novos: Dict[str, Any] | None = None,
) -> None:
    detalhes = {}
    if dados_anteriores is not None:
        detalhes["antes"] = dados_anteriores
    if dados_novos is not None:
        detalhes["depois"] = dados_novos
    OrganizacaoAtividadeLog.objects.create(
        organizacao=organizacao,
        usuario=usuario,
        acao=acao,
        detalhes=json.dumps(detalhes) if detalhes else "",
    )
