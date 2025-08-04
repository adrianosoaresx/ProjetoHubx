from __future__ import annotations

import csv
import json
from datetime import timedelta
from typing import Sequence

from celery import shared_task  # type: ignore
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .metrics import chat_exportacoes_total
from .models import ChatChannel, RelatorioChatExport


@shared_task
def exportar_historico_chat(
    channel_id: str,
    formato: str,
    inicio: str | None = None,
    fim: str | None = None,
    tipos: Sequence[str] | None = None,
    relatorio_id: str | None = None,
) -> str:
    """Gera e salva um arquivo com o histórico de mensagens do canal.

    Args:
        channel_id: ID do ``ChatChannel`` a ser exportado.
        formato: ``"json"`` ou ``"csv"``.
        inicio: filtro opcional de data inicial (ISO8601).
        fim: filtro opcional de data final (ISO8601).
        tipos: lista de tipos de mensagem a incluir.
        relatorio_id: identificador do ``RelatorioChatExport`` associado.

    Returns:
        URL pública para download do arquivo gerado.
    """

    channel = ChatChannel.objects.get(pk=channel_id)
    rel = RelatorioChatExport.objects.get(pk=relatorio_id)
    qs = channel.messages.filter(hidden_at__isnull=True).select_related("remetente")
    if inicio:
        qs = qs.filter(created__gte=inicio)
    if fim:
        qs = qs.filter(created__lte=fim)
    if tipos:
        qs = qs.filter(tipo__in=tipos)
    data = [
        {
            "id": str(m.id),
            "remetente": m.remetente.username,
            "tipo": m.tipo,
            "conteudo": m.conteudo if m.tipo == "text" else (m.arquivo.url if m.arquivo else ""),
            "created": m.created.isoformat(),
        }
        for m in qs
    ]
    buffer = ""
    filename = f"chat_exports/{channel.id}.{formato}"
    if formato == "csv":
        from io import StringIO

        sio = StringIO()
        writer = csv.DictWriter(sio, fieldnames=["id", "remetente", "tipo", "conteudo", "created"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        buffer = sio.getvalue()
    else:
        buffer = json.dumps(data)
    path = default_storage.save(filename, ContentFile(buffer.encode()))
    rel.arquivo_url = default_storage.url(path)
    rel.status = "concluido"
    rel.save(update_fields=["arquivo_url", "status", "modified"])
    chat_exportacoes_total.labels(formato=formato).inc()
    return rel.arquivo_url


@shared_task
def limpar_exports_antigos() -> None:
    """Remove arquivos de exportação com mais de 30 dias."""

    limite = timezone.now() - timedelta(days=30)
    antigos = RelatorioChatExport.objects.filter(created__lt=limite)
    for rel in antigos:
        if rel.arquivo_url:
            try:
                default_storage.delete(rel.arquivo_url)
            except Exception:
                pass
        rel.delete()
