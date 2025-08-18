from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _

from configuracoes.services import get_user_preferences

from ..models import Canal, NotificationLog, NotificationTemplate
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

    qs = NotificationTemplate.objects.filter(codigo=template_codigo)
    template = qs.first()
    if not template:
        raise ValueError(_("Template '%(codigo)s' não encontrado") % {"codigo": template_codigo})

    subject, body = render_template(template, context)

    prefs = get_user_preferences(user, escopo_tipo, escopo_id)

    canais: list[str] = []
    if template.canal in {Canal.EMAIL, Canal.TODOS} and prefs.receber_notificacoes_email:
        canais.append(Canal.EMAIL)
    if (
        template.canal in {Canal.PUSH, Canal.TODOS}
        and prefs.receber_notificacoes_push
    ):
        canais.append(Canal.PUSH)
    if template.canal in {Canal.WHATSAPP, Canal.TODOS} and prefs.receber_notificacoes_whatsapp:
        canais.append(Canal.WHATSAPP)

    if not canais:
        raise ValueError(_("Canais desabilitados pelo usuário"))

    for canal in canais:
        log = NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            destinatario=_mask_email(user.email) if canal == Canal.EMAIL else "",
        )
        enviar_imediato = False
        if canal == Canal.EMAIL:
            enviar_imediato = prefs.frequencia_notificacoes_email == "imediata"
        elif canal == Canal.WHATSAPP:
            enviar_imediato = prefs.frequencia_notificacoes_whatsapp == "imediata"
        elif canal == Canal.PUSH:
            enviar_imediato = prefs.frequencia_notificacoes_push == "imediata"
        if enviar_imediato:
            enviar_notificacao_async.delay(subject, body, str(log.id))
