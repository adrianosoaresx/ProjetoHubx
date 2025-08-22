from __future__ import annotations

from typing import Any, Dict
import uuid

import json
import csv


from django.db.models import Model
from django.http import HttpResponse

from .models import Organizacao, OrganizacaoAtividadeLog, OrganizacaoChangeLog


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
    detalhes: Dict[str, Any] = {}
    if dados_anteriores is not None:
        detalhes["antes"] = dados_anteriores
    if dados_novos is not None:
        detalhes["depois"] = dados_novos
    OrganizacaoAtividadeLog.objects.create(
        organizacao=organizacao,
        usuario=usuario,
        acao=acao,
        detalhes=detalhes or {},
    )


def exportar_logs_csv(organizacao: Organizacao) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="organizacao_{organizacao.pk}_logs.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "tipo",
        "campo/acao",
        "valor_antigo",
        "valor_novo",
        "usuario",
        "data",
    ])
    for log in (
        OrganizacaoChangeLog.all_objects.filter(organizacao=organizacao)
        .order_by("-created_at")
    ):
        writer.writerow(
            [
                "change",
                log.campo_alterado,
                log.valor_antigo,
                log.valor_novo,
                getattr(log.alterado_por, "email", ""),
                log.created_at.isoformat(),
            ]
        )
    for log in (
        OrganizacaoAtividadeLog.all_objects.filter(organizacao=organizacao)
        .order_by("-created_at")
    ):
        writer.writerow(
            [
                "activity",
                log.acao,
                "",
                "",
                getattr(log.usuario, "email", ""),
                log.created_at.isoformat(),
            ]
        )
    return response
