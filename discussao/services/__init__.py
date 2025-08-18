from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from accounts.models import User

from ..models import (
    CategoriaDiscussao,
    Denuncia,
    InteracaoDiscussao,
    RespostaDiscussao,
    TopicoDiscussao,
)


class DiscussaoError(Exception):
    """Erro genérico para regras de negócio do módulo de discussão."""


def criar_topico(
    *,
    categoria: CategoriaDiscussao,
    titulo: str,
    conteudo: str,
    autor: User,
    publico_alvo: int,
    **extra: Any,
) -> TopicoDiscussao:
    """Cria um tópico de discussão."""
    return TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo=titulo,
        conteudo=conteudo,
        autor=autor,
        publico_alvo=publico_alvo,
        **extra,
    )


def responder_topico(
    *,
    topico: TopicoDiscussao,
    autor: User,
    conteudo: str,
    reply_to: RespostaDiscussao | None = None,
    arquivo: Any | None = None,
) -> RespostaDiscussao:
    if topico.fechado:
        raise DiscussaoError(_("Tópico fechado para novas respostas."))
    return RespostaDiscussao.objects.create(
        topico=topico,
        autor=autor,
        conteudo=conteudo,
        reply_to=reply_to,
        arquivo=arquivo,
    )


def votar_interacao(*, user: User, obj: models.Model, valor: int) -> InteracaoDiscussao:
    ct = ContentType.objects.get_for_model(obj)
    interacao, _ = InteracaoDiscussao.objects.get_or_create(
        user=user, content_type=ct, object_id=obj.pk
    )
    if interacao.valor == valor:
        interacao.delete()
        return interacao
    interacao.valor = valor
    interacao.save(update_fields=["valor"])
    return interacao


def marcar_resolucao(*, topico: TopicoDiscussao, resposta: RespostaDiscussao, user: User) -> TopicoDiscussao:
    if user != topico.autor and user.user_type not in {"admin", "root"}:
        raise PermissionDenied
    with transaction.atomic():
        topico.melhor_resposta = resposta
        topico.resolvido = True
        topico.save(update_fields=["melhor_resposta", "resolvido"])
    return topico


def denunciar_conteudo(
    *, user: User, content_object: models.Model, motivo: str
) -> Denuncia:
    ct = ContentType.objects.get_for_model(content_object)
    if Denuncia.objects.filter(
        user=user, content_type=ct, object_id=content_object.pk
    ).exists():
        raise DiscussaoError(_("Denúncia já registrada."))
    return Denuncia.objects.create(
        user=user,
        content_type=ct,
        object_id=content_object.pk,
        motivo=motivo,
    )
