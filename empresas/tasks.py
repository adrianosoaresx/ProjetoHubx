from __future__ import annotations

import sentry_sdk
from celery import shared_task
from django.dispatch import Signal, receiver

from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from services.cnpj_validator import CNPJValidationError, validar_cnpj

from .models import AvaliacaoEmpresa, Empresa

nova_avaliacao = Signal()  # args: avaliacao


@shared_task
def validar_cnpj_async(cnpj: str) -> None:
    try:
        validar_cnpj(cnpj)
    except CNPJValidationError as exc:  # pragma: no cover - rede externa
        sentry_sdk.capture_exception(exc)


@shared_task
def validar_cnpj_empresa(empresa_id: str) -> None:
    try:
        empresa = Empresa.objects.get(pk=empresa_id)
    except Empresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    try:
        valido, fonte = validar_cnpj(empresa.cnpj)
    except CNPJValidationError as exc:  # pragma: no cover - rede externa
        sentry_sdk.capture_exception(exc)
        return
    if valido:
        empresa.validado_em = timezone.now()
        empresa.fonte_validacao = fonte
        empresa.save(update_fields=["validado_em", "fonte_validacao"])


@shared_task
def notificar_responsavel(avaliacao_id: str) -> None:
    try:
        avaliacao = AvaliacaoEmpresa.objects.select_related("empresa__usuario").get(pk=avaliacao_id)
    except AvaliacaoEmpresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    email = avaliacao.empresa.usuario.email
    if not email:
        return
    try:
        enviar_para_usuario(
            avaliacao.empresa.usuario,
            "nova_avaliacao_empresa",
            {"empresa": avaliacao.empresa.nome},
        )
    except Exception as exc:  # pragma: no cover - integração externa
        sentry_sdk.capture_exception(exc)


@shared_task
def criar_post_empresa(empresa_id: str) -> None:
    from feed.models import Post  # import local para evitar dependências circulares

    try:
        empresa = Empresa.objects.select_related("usuario", "organizacao").get(pk=empresa_id)
    except Empresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return

    Post.objects.create(
        autor=empresa.usuario,
        organizacao=empresa.organizacao,
        tipo_feed="global",
        conteudo=f"Nova empresa cadastrada: {empresa.nome}",
    )


@shared_task
def criar_post_avaliacao(avaliacao_id: str) -> None:
    from feed.models import Post  # import local para evitar dependências circulares

    try:
        avaliacao = AvaliacaoEmpresa.objects.select_related("empresa__organizacao", "empresa", "usuario").get(
            pk=avaliacao_id
        )
    except AvaliacaoEmpresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    if avaliacao.nota < 4:
        return
    Post.objects.create(
        autor=avaliacao.usuario,
        organizacao=avaliacao.empresa.organizacao,
        tipo_feed="global",
        conteudo=f"{avaliacao.usuario} avaliou {avaliacao.empresa.nome} com nota {avaliacao.nota}",
    )


@receiver(nova_avaliacao)
def _on_nova_avaliacao(sender, avaliacao: AvaliacaoEmpresa, **kwargs) -> None:
    notificar_responsavel.delay(str(avaliacao.id))
    criar_post_avaliacao.delay(str(avaliacao.id))
