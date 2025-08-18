from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from agenda.models import Evento

from ..models import TopicoDiscussao


def criar_evento_para_topico(
    topico: TopicoDiscussao,
    user: User,
    titulo: str,
    inicio: datetime,
    fim: datetime,
    descricao: str = "",
) -> Evento:
    """Cria um evento na Agenda vinculado a um tópico de discussão."""
    if user != topico.autor and user.get_tipo_usuario not in {"admin", "root"}:
        raise PermissionDenied
    if not settings.FEATURE_DISCUSSAO_AGENDA:
        raise PermissionDenied(_("Integração com Agenda desativada."))
    link = f"/discussao/topicos/{topico.id}/"
    descricao_completa = f"{descricao}\n\n{link}" if descricao else link
    return Evento.objects.create(
        organizacao=topico.categoria.organizacao,
        nucleo=topico.nucleo,
        coordenador=user,
        titulo=titulo,
        descricao=descricao_completa,
        data_inicio=inicio,
        data_fim=fim,
        local=_("A definir"),
        cidade="São Paulo",
        estado="SP",
        cep="00000-000",
        status=0,
        publico_alvo=0,
        numero_convidados=0,
        numero_presentes=0,
        contato_nome=user.get_full_name() or user.email,
    )
