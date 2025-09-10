from __future__ import annotations

import logging
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from tokens.models import TokenAcesso

from .metrics import convites_gerados_total
from .models import ConviteNucleo, Nucleo, ParticipacaoNucleo

User = get_user_model()
logger = logging.getLogger(__name__)


def criar_participacoes_membros(nucleo: Nucleo, membros: Iterable[User]) -> list[ParticipacaoNucleo]:
    """Cria participações aprovadas para a lista de membros fornecida."""
    participacoes: list[ParticipacaoNucleo] = []
    for user in membros:
        part, _ = ParticipacaoNucleo.objects.get_or_create(nucleo=nucleo, user=user)
        part.status = "ativo"
        part.save(update_fields=["status"])
        participacoes.append(part)
    return participacoes


def gerar_convite_nucleo(user: User, nucleo: Nucleo, email: str, papel: str) -> ConviteNucleo:
    """Gera um convite para o núcleo respeitando a cota diária do emissor."""

    limite = getattr(settings, "CONVITE_NUCLEO_DIARIO_LIMITE", 5)
    cache_key = f"convites_nucleo:{user.id}:{timezone.now().date()}"
    count = cache.get(cache_key, 0)
    if count >= limite:
        raise ValueError("limite diário de convites atingido")
    cache.set(cache_key, count + 1, 24 * 60 * 60)

    token = TokenAcesso.objects.create(
        gerado_por=user,
        tipo_destino=(
            TokenAcesso.TipoUsuario.COORDENADOR if papel == "coordenador" else TokenAcesso.TipoUsuario.NUCLEADO
        ),
        organizacao=nucleo.organizacao,
        data_expiracao=timezone.now() + timedelta(days=7),
    )
    token.nucleos.add(nucleo)
    convite = ConviteNucleo.objects.create(
        token=token.codigo,
        token_obj=token,
        email=email,
        papel=papel,
        nucleo=nucleo,
        data_expiracao=token.data_expiracao,
    )
    convites_gerados_total.inc()
    logger.info(
        "convite_gerado",
        extra={
            "convite_id": str(convite.pk),
            "nucleo_id": str(nucleo.pk),
            "emissor_id": str(user.pk),
            "email": email,
            "papel": papel,
        },
    )
    return convite


def registrar_uso_convite(convite: ConviteNucleo) -> None:
    """Registra um uso do convite respeitando o limite diário.

    Usa o cache para contar quantas vezes o convite foi utilizado no dia
    corrente. Levanta ``ValueError`` quando o limite é ultrapassado.
    """

    cache_key = f"convite_uso:{convite.id}:{timezone.now().date()}"
    count = cache.get(cache_key, 0)
    if count >= convite.limite_uso_diario:
        raise ValueError("limite diário de uso do convite atingido")
    # Armazena por 24h para reiniciar a contagem a cada dia
    cache.set(cache_key, count + 1, 24 * 60 * 60)
