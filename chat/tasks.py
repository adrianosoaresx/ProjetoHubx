from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import timedelta
from typing import Sequence

from celery import shared_task  # type: ignore
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .metrics import (
    chat_exportacoes_total,
    chat_mensagens_removidas_retencao_total,
    chat_resumo_geracao_segundos,
    chat_resumos_total,
)
from .models import (
    ChatAttachment,
    ChatChannel,
    ChatModerationLog,
    RelatorioChatExport,
    ResumoChat,
    TrendingTopic,
)

User = get_user_model()


def _scan_file(path: str) -> bool:  # pragma: no cover - depends on external service
    try:
        import clamd  # type: ignore

        cd = clamd.ClamdNetworkSocket()
        result = cd.scan(path)
        if result:
            return any(status == "FOUND" for _, (status, _) in result.items())
    except Exception:
        return False
    return False


@shared_task
def aplicar_politica_retencao() -> None:
    """Aplica a política de retenção de mensagens por canal."""

    agora = timezone.now()
    for canal in ChatChannel.objects.filter(retencao_dias__isnull=False):
        limite = agora - timedelta(days=canal.retencao_dias or 0)
        mensagens_qs = canal.messages.filter(created_at__lt=limite)
        ids = list(mensagens_qs.values_list("id", flat=True).iterator())
        if not ids:
            continue

        # Remove anexos associados às mensagens, garantindo cascata controlada
        ChatAttachment.objects.filter(mensagem_id__in=ids).delete()
        mensagens_qs.delete()

        chat_mensagens_removidas_retencao_total.inc(len(ids))
        moderator = canal.participants.filter(is_admin=True).first()
        user = moderator.user if moderator else User.objects.filter(is_staff=True).first()
        if user:
            logs = [
                ChatModerationLog(
                    message_id=mid,
                    action="retencao",
                    moderator=user,
                )
                for mid in ids
            ]
            ChatModerationLog.objects.bulk_create(logs)


@shared_task
def scan_existing_attachments() -> None:
    """Escaneia anexos antigos em busca de malware."""

    for att in ChatAttachment.objects.filter(infected=False):
        try:
            if _scan_file(att.arquivo.path):
                att.infected = True
                att.save(update_fields=["infected"])
        except Exception:
            continue


@shared_task
def gerar_resumo_chat(canal_id: str, periodo: str) -> str:
    inicio = timezone.now()
    channel = ChatChannel.objects.get(pk=canal_id)
    limite = timezone.now() - (timedelta(days=1) if periodo == "diario" else timedelta(days=7))
    mensagens = channel.messages.filter(created_at__gte=limite, hidden_at__isnull=True, tipo="text").order_by(
        "created_at"
    )
    texto = "\n".join(m.conteudo for m in mensagens)
    resumo = texto[:500]
    resumo_obj = ResumoChat.objects.create(
        canal=channel,
        periodo=periodo,
        conteudo=resumo,
        detalhes={"total_mensagens": mensagens.count()},
    )
    duracao = (timezone.now() - inicio).total_seconds()
    chat_resumo_geracao_segundos.labels(periodo=periodo).observe(duracao)
    chat_resumos_total.labels(periodo=periodo).inc()
    return str(resumo_obj.id)


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
        qs = qs.filter(created_at__gte=inicio)
    if fim:
        qs = qs.filter(created_at__lte=fim)
    if tipos:
        tipos = [t for t in tipos if t]
        if tipos:
            qs = qs.filter(tipo__in=tipos)
    data = [
        {
            "id": str(m.id),
            "remetente": m.remetente.username,
            "tipo": m.tipo,
            "conteudo": m.conteudo if m.tipo == "text" else (m.arquivo.url if m.arquivo else ""),
            "created_at": m.created_at.isoformat(),
        }
        for m in qs
    ]
    buffer = ""
    filename = f"chat_exports/{channel.id}.{formato}"
    if formato == "csv":
        from io import StringIO

        sio = StringIO()
        writer = csv.DictWriter(sio, fieldnames=["id", "remetente", "tipo", "conteudo", "created_at"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        buffer = sio.getvalue()
    else:
        buffer = json.dumps(data)
    path = default_storage.save(filename, ContentFile(buffer.encode()))
    rel.arquivo_path = path
    rel.arquivo_url = default_storage.url(path)
    rel.status = "concluido"
    rel.save(update_fields=["arquivo_path", "arquivo_url", "status", "updated_at"])
    chat_exportacoes_total.labels(formato=formato).inc()
    return rel.arquivo_url


@shared_task
def limpar_exports_antigos() -> None:
    """Remove arquivos de exportação com mais de 30 dias."""

    limite = timezone.now() - timedelta(days=30)
    antigos = RelatorioChatExport.objects.filter(created_at__lt=limite)
    for rel in antigos:
        if rel.arquivo_path:
            try:
                default_storage.delete(rel.arquivo_path)
            except Exception:
                pass
        rel.delete()


@shared_task
def calcular_trending_topics(canal_id: str, dias: int = 7) -> list[tuple[str, int]]:
    """Calcula palavras mais frequentes em mensagens recentes de um canal."""

    channel = ChatChannel.objects.get(pk=canal_id)
    inicio = timezone.now() - timedelta(days=dias)
    mensagens = channel.messages.filter(created_at__gte=inicio, hidden_at__isnull=True, tipo="text")
    counter: Counter[str] = Counter()
    stop_words = {
        "de",
        "a",
        "o",
        "que",
        "e",
        "do",
        "da",
        "em",
        "um",
        "para",
        "com",
        "na",
        "no",
        "os",
        "se",
        "por",
        "não",
    }
    for msg in mensagens:
        palavras = re.findall(r"[\wÀ-ÿ]+", msg.conteudo.lower())
        for palavra in palavras:
            if len(palavra) < 3 or palavra in stop_words:
                continue
            counter[palavra] += 1

    periodo_fim = timezone.now()
    TrendingTopic.objects.filter(canal=channel, periodo_inicio__gte=inicio).delete()
    topics = []
    for palavra, freq in counter.most_common(10):
        TrendingTopic.objects.create(
            canal=channel,
            palavra=palavra,
            frequencia=freq,
            periodo_inicio=inicio,
            periodo_fim=periodo_fim,
        )
        topics.append((palavra, freq))
    return topics
