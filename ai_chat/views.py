from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from rest_framework.test import APIRequestFactory

from .api import ChatMessageViewSet
from .models import ChatMessage, ChatSession
from organizacoes.models import Organizacao


def _build_plotly_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    if "figure" in payload and isinstance(payload["figure"], dict):
        return payload

    chart = payload.get("chart") if isinstance(payload.get("chart"), dict) else None
    if chart and isinstance(chart.get("figure"), dict):
        return chart

    return None


def _serialize_message(message: ChatMessage) -> dict[str, Any]:
    parsed_content: Any | None = None
    display_content = message.content
    plotly_payload: dict[str, Any] | None = None

    try:
        parsed_content = json.loads(message.content)
    except (TypeError, ValueError):
        parsed_content = None

    if isinstance(parsed_content, dict):
        plotly_payload = _build_plotly_payload(parsed_content)
        if message.role == ChatMessage.Role.TOOL:
            display_content = json.dumps(
                {k: v for k, v in parsed_content.items() if k != "chart"},
                ensure_ascii=False,
                indent=2,
            )
        else:
            display_content = parsed_content.get("content") or message.content

    return {
        "id": str(message.id),
        "role": message.role,
        "created_at": message.created_at,
        "content": display_content,
        "plotly_payload": plotly_payload,
        "plotly_script_id": f"plotly-figure-{message.id}" if plotly_payload else None,
        "plotly_container_id": f"plotly-container-{message.id}" if plotly_payload else None,
        "is_user": message.role == ChatMessage.Role.USER,
        "is_tool": message.role == ChatMessage.Role.TOOL,
    }


class ChatPageView(LoginRequiredMixin, TemplateView):
    template_name = "ai_chat/chat.html"

    def _get_or_create_session(self):
        user = self.request.user
        organizacao_id = getattr(user, "organizacao_id", None)
        if not organizacao_id:
            return None

        organizacao = Organizacao.objects.get(id=organizacao_id)
        session = ChatSession.objects.filter(
            usuario=user,
            organizacao=organizacao,
            status=ChatSession.Status.ACTIVE,
        ).first()

        if not session:
            session = ChatSession.objects.create(usuario=user, organizacao=organizacao)

        return session

    def get_context_data(self, **kwargs):  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        session = self._get_or_create_session()
        if not session:
            context["missing_organization"] = True
            return context

        messages = session.messages.exclude(role=ChatMessage.Role.TOOL)

        context.update(
            {
                "session": session,
                "chat_messages": [_serialize_message(msg) for msg in messages],
            }
        )
        return context


@login_required
@require_POST
def send_message(request: HttpRequest, session_id: str) -> HttpResponse:
    session = get_object_or_404(
        ChatSession,
        pk=session_id,
        usuario=request.user,
        organizacao=getattr(request.user, "organizacao", None),
        status=ChatSession.Status.ACTIVE,
    )

    message_text = (request.POST.get("message") or "").strip()
    if not message_text:
        return HttpResponseBadRequest("Mensagem obrigatória.")

    api_request = APIRequestFactory().post(
        "/api/ai-chat/messages/",
        {"session": str(session.id), "message": message_text},
        format="json",
    )
    api_request.user = request.user
    api_request._force_auth_user = request.user

    response = ChatMessageViewSet.as_view({"post": "create"})(api_request)
    if hasattr(response, "render"):
        response.render()

    if response.status_code >= 400:
        return JsonResponse(response.data, status=response.status_code, safe=False)

    message_ids = [
        message.get("id")
        for message in response.data.get("messages", [])
        if isinstance(message, dict) and message.get("id")
    ]
    queryset = (
        ChatMessage.objects.filter(id__in=message_ids)
        .exclude(role=ChatMessage.Role.TOOL)
        .order_by("created_at")
    )
    context = {"chat_messages": [_serialize_message(msg) for msg in queryset]}

    return render(request, "ai_chat/_messages.html", context)


@login_required
@require_POST
def clear_session_messages(request: HttpRequest, session_id: str) -> HttpResponse:
    session = get_object_or_404(
        ChatSession,
        pk=session_id,
        usuario=request.user,
        organizacao=getattr(request.user, "organizacao", None),
        status=ChatSession.Status.ACTIVE,
    )

    session.messages.all().delete()

    return render(request, "ai_chat/_messages.html", {"chat_messages": []})
