from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _

from ..models import (
    Canal,
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    UserNotificationPreference,
)
from ..tasks import enviar_notificacao_async

logger = logging.getLogger(__name__)


def render_template(template: NotificationTemplate, context: dict[str, Any]) -> tuple[str, str]:
    subject_tpl = Template(template.assunto)
    body_tpl = Template(template.corpo)
    ctx = Context(context)
    return subject_tpl.render(ctx), body_tpl.render(ctx)


def _mask_email(email: str) -> str:
    nome, _, dominio = email.partition("@")
    prefixo = nome[:2]
    return f"{prefixo}***@{dominio}" if dominio else email


def enviar_para_usuario(
    user: Any,
    template_codigo: str,
    context: dict[str, Any],
    escopo_tipo: str | None = None,
    escopo_id: str | None = None,
) -> None:
    if not getattr(settings, "NOTIFICATIONS_ENABLED", True):
        return

    qs = NotificationTemplate.objects.filter(codigo=template_codigo, ativo=True)
    template = qs.first()
    if not template:
        raise ValueError(_("Template '%(codigo)s' não encontrado") % {"codigo": template_codigo})

    subject, body = render_template(template, context)

    prefs, _created = UserNotificationPreference.objects.get_or_create(user=user)

    canais: list[str] = []
    canais_desabilitados: list[str] = []

    if template.canal in {Canal.EMAIL, Canal.TODOS}:
        if prefs.email:
            canais.append(Canal.EMAIL)
        else:
            canais_desabilitados.append(Canal.EMAIL)

    if template.canal in {Canal.PUSH, Canal.TODOS}:
        if prefs.push:
            canais.append(Canal.PUSH)
        else:
            canais_desabilitados.append(Canal.PUSH)

    if template.canal in {Canal.WHATSAPP, Canal.TODOS}:
        if prefs.whatsapp:
            canais.append(Canal.WHATSAPP)
        else:
            canais_desabilitados.append(Canal.WHATSAPP)

    for canal in canais_desabilitados:
        NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            destinatario=_mask_email(user.email) if canal == Canal.EMAIL else "",
            status=NotificationStatus.FALHA,
            erro=_("Canais desabilitados pelo usuário"),
            corpo_renderizado=body,
        )

    if not canais:
        return

    for canal in canais:
        log = NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            destinatario=_mask_email(user.email) if canal == Canal.EMAIL else "",
            corpo_renderizado=body,
        )
        enviar_notificacao_async.delay(subject, body, str(log.id))
