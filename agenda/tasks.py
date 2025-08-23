from __future__ import annotations

import logging
from celery import shared_task
from django.utils import timezone
from django.core.files.storage import default_storage

from .models import Evento, MaterialDivulgacaoEvento, BriefingEvento, EventoLog
from notificacoes.services.notificacoes import enviar_para_usuario

logger = logging.getLogger(__name__)


@shared_task
def promover_lista_espera(evento_id: int) -> None:
    evento = Evento.objects.filter(pk=evento_id).first()
    if not evento or not evento.participantes_maximo:
        return
    vagas = evento.participantes_maximo - evento.inscricoes.filter(status="confirmada").count()
    if vagas <= 0:
        return
    pendentes = evento.inscricoes.filter(status="pendente").order_by("posicao_espera")[:vagas]
    for ins in pendentes:
        ins.status = "confirmada"
        ins.posicao_espera = None
        ins.data_confirmacao = timezone.now()
        ins.save(update_fields=["status", "posicao_espera", "data_confirmacao", "updated_at"])

        enviar_para_usuario(
            ins.user,
            "evento_lista_espera_promovido",
            {"evento": {"id": evento.pk, "titulo": evento.titulo}},
            escopo_tipo="agenda.Evento",
            escopo_id=str(evento.pk),
        )
        EventoLog.objects.create(
            evento=evento,
            usuario=ins.user,
            acao="inscricao_promovida",
            detalhes={"notificacao": True},
        )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def upload_material_divulgacao(self, material_id: int) -> None:
    """Realiza upload assíncrono do material para o storage padrão."""
    material = MaterialDivulgacaoEvento.objects.filter(pk=material_id).first()
    if not material or not material.arquivo:
        return
    try:
        default_storage.save(material.arquivo.name, material.arquivo.file)
    except Exception as exc:  # pragma: no cover - rede/storage
        logger.exception("Falha no upload do material %s", material_id)
        raise exc
    logger.info("Upload do material %s concluído", material_id)


@shared_task
def notificar_briefing_status(briefing_id: int, status: str) -> None:
    """Notifica mudança de status do briefing."""
    briefing = BriefingEvento.objects.filter(pk=briefing_id).select_related("evento__coordenador").first()
    if not briefing:
        return
    logger.info("Briefing %s mudou para %s", briefing_id, status)
