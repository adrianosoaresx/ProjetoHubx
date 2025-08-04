from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import Evento


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
        ins.save(update_fields=["status", "posicao_espera", "data_confirmacao", "modified"])
