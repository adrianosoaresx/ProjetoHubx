from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.template import Context, Template
from django.utils import timezone

from ..models import NotificationLog, NotificationStatus, NotificationTemplate, UserNotificationPreference
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

    template = NotificationTemplate.objects.get(codigo=template_codigo, ativo=True)
    subject, body = render_template(template, context)

    prefs, _ = UserNotificationPreference.objects.get_or_create(user=user)
    canais = []
    if template.canal in {"email", "todos"} and prefs.email:
        canais.append("email")
    if template.canal in {"push", "todos"} and prefs.push:
        canais.append("push")
    if template.canal in {"whatsapp", "todos"} and prefs.whatsapp:
        canais.append("whatsapp")

    for canal in canais:
        log = NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            status=NotificationStatus.ENVIADA,
            data_envio=timezone.now(),
        )
        enviar_notificacao_async.delay(user.id, template.id, canal, subject, body, log.id)  # type: ignore[attr-defined]
