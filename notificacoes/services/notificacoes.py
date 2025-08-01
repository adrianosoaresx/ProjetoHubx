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


def enviar_para_usuario(user: Any, template_codigo: str, context: dict[str, Any]) -> None:
    if not getattr(settings, "NOTIFICATIONS_ENABLED", True):
        return

    qs = NotificationTemplate.objects.filter(codigo=template_codigo, ativo=True)
    template = qs.first()
    if not template:
        raise ValueError(_("Template '%(codigo)s' não encontrado") % {"codigo": template_codigo})

    subject, body = render_template(template, context)

    prefs, _created = UserNotificationPreference.objects.get_or_create(user=user)

    canais: list[str] = []
    if template.canal in {Canal.EMAIL, Canal.TODOS} and prefs.email:
        canais.append(Canal.EMAIL)
    if template.canal in {Canal.PUSH, Canal.TODOS} and prefs.push:
        canais.append(Canal.PUSH)
    if template.canal in {Canal.WHATSAPP, Canal.TODOS} and prefs.whatsapp:
        canais.append(Canal.WHATSAPP)

    if not canais:
        NotificationLog.objects.create(
            user=user,
            template=template,
            canal=template.canal,
            status=NotificationStatus.FALHA,
            erro=_("Canais desabilitados pelo usuário"),
        )
        return

    for canal in canais:
        log = NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            status=NotificationStatus.PENDENTE,
        )
        enviar_notificacao_async.delay(
            user.id,
            str(template.id),
            canal,
            subject,
            body,
            str(log.id),
        )
