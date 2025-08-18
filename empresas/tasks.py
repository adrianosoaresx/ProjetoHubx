from __future__ import annotations

import sentry_sdk
from celery import shared_task
from django.dispatch import Signal, receiver

from django.utils import timezone

from notificacoes.services.notificacoes import enviar_para_usuario

from services.cnpj_validator import CNPJValidationError, validar_cnpj

from .models import AvaliacaoEmpresa, Empresa

nova_avaliacao = Signal()  # args: avaliacao


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def validar_cnpj_empresa(self, empresa_id: str) -> None:
    try:
        empresa = Empresa.objects.get(pk=empresa_id)
        valido, fonte = validar_cnpj(empresa.cnpj)
        if valido:
            empresa.validado_em = timezone.now()
            empresa.fonte_validacao = fonte
            empresa.save(update_fields=["validado_em", "fonte_validacao"])
    except Empresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    except CNPJValidationError as exc:  # pragma: no cover - rede externa
        sentry_sdk.capture_exception(exc)
        return
    except Exception as exc:  # pragma: no cover - falha inesperada
        if self.request.retries >= self.max_retries:
            sentry_sdk.capture_exception(exc)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def notificar_responsavel(self, avaliacao_id: str) -> None:
    try:
        avaliacao = AvaliacaoEmpresa.objects.select_related("empresa__usuario").get(pk=avaliacao_id)
        email = avaliacao.empresa.usuario.email
        if not email:
            return
        enviar_para_usuario(
            avaliacao.empresa.usuario,
            "nova_avaliacao_empresa",
            {"empresa": avaliacao.empresa.nome},
        )
    except AvaliacaoEmpresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    except Exception as exc:  # pragma: no cover - integração externa
        if self.request.retries >= self.max_retries:
            sentry_sdk.capture_exception(exc)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def criar_post_empresa(self, empresa_id: str) -> None:
    from feed.models import Post  # import local para evitar dependências circulares

    try:
        empresa = Empresa.objects.select_related("usuario", "organizacao").get(pk=empresa_id)
        Post.objects.create(
            autor=empresa.usuario,
            organizacao=empresa.organizacao,
            tipo_feed="global",
            conteudo=f"Nova empresa cadastrada: {empresa.nome}",
        )
    except Empresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    except Exception as exc:  # pragma: no cover - falha inesperada
        if self.request.retries >= self.max_retries:
            sentry_sdk.capture_exception(exc)
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def criar_post_avaliacao(self, avaliacao_id: str) -> None:
    from feed.models import Post  # import local para evitar dependências circulares

    try:
        avaliacao = AvaliacaoEmpresa.objects.select_related(
            "empresa__organizacao", "empresa", "usuario"
        ).get(pk=avaliacao_id)
        if avaliacao.nota < 4:
            return
        Post.objects.create(
            autor=avaliacao.usuario,
            organizacao=avaliacao.empresa.organizacao,
            tipo_feed="global",
            conteudo=f"{avaliacao.usuario} avaliou {avaliacao.empresa.nome} com nota {avaliacao.nota}",
        )
    except AvaliacaoEmpresa.DoesNotExist as exc:  # pragma: no cover - condição rara
        sentry_sdk.capture_exception(exc)
        return
    except Exception as exc:  # pragma: no cover - falha inesperada
        if self.request.retries >= self.max_retries:
            sentry_sdk.capture_exception(exc)
        raise


@receiver(nova_avaliacao)
def _on_nova_avaliacao(sender, avaliacao: AvaliacaoEmpresa, **kwargs) -> None:
    notificar_responsavel.delay(str(avaliacao.id))
    criar_post_avaliacao.delay(str(avaliacao.id))
