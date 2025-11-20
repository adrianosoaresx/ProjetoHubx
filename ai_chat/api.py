from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Mapping
from typing import Any, Iterable

from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.functional import Promise
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from ai_chat.settings import get_ai_chat_settings
from core.cache import get_cache_version
from openai import OpenAI

from .models import ChatMessage, ChatSession
from . import services as chat_services
from .metrics import (
    chat_openai_errors_total,
    chat_openai_latency_seconds,
    chat_tool_errors_total,
    chat_tool_latency_seconds,
)


logger = logging.getLogger(__name__)


SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "Você é um assistente que utiliza ferramentas para responder com dados atualizados "
        "da organização. Utilize as funções disponíveis quando necessário e responda em "
        "português."
    ),
}


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Promise):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_json_value(item) for item in value]

    return str(value)


def _build_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_membership_totals",
                "description": "Obtém totais de membros e dados para gráfico da organização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {
                            "type": "string",
                            "description": "Identificador da organização.",
                        }
                    },
                    "required": ["organizacao_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_event_status_totals",
                "description": "Retorna totais de eventos por status da organização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {
                            "type": "string",
                            "description": "Identificador da organização.",
                        }
                    },
                    "required": ["organizacao_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_monthly_members",
                "description": "Evolução mensal de novos membros da organização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {"type": "string"},
                        "months": {
                            "type": "integer",
                            "description": "Quantidade de meses de histórico.",
                        },
                    },
                    "required": ["organizacao_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_nucleo_metrics",
                "description": "Métricas detalhadas de um núcleo da organização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {"type": "string"},
                        "nucleo_id": {"type": "string"},
                    },
                    "required": ["organizacao_id", "nucleo_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_organizacao_description",
                "description": "Descrição e metadados básicos da organização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {"type": "string"},
                    },
                    "required": ["organizacao_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_organizacao_nucleos_context",
                "description": "Lista núcleos ativos e dados relevantes da organização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {"type": "string"},
                    },
                    "required": ["organizacao_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_future_events_context",
                "description": "Eventos futuros da organização com filtros opcionais.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "organizacao_id": {"type": "string"},
                        "limit": {"type": "integer"},
                        "nucleo_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de IDs de núcleos para filtrar.",
                        },
                    },
                    "required": ["organizacao_id"],
                },
            },
        },
    ]


TOOL_WRAPPERS: dict[str, Any] = {
    "get_membership_totals": chat_services.get_membership_totals,
    "get_event_status_totals": chat_services.get_event_status_totals,
    "get_monthly_members": chat_services.get_monthly_members,
    "get_nucleo_metrics": chat_services.get_nucleo_metrics,
    "get_organizacao_description": chat_services.get_organizacao_description,
    "get_organizacao_nucleos_context": chat_services.get_organizacao_nucleos_context,
    "get_future_events_context": chat_services.get_future_events_context,
}


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ["id", "status", "created_at", "updated_at"]
        read_only_fields = fields


class ChatMessageSerializer(serializers.ModelSerializer):
    session = serializers.PrimaryKeyRelatedField(queryset=ChatSession.objects.all())
    message = serializers.CharField(write_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "session",
            "role",
            "message",
            "content",
            "tool_call_id",
            "created_at",
        ]
        read_only_fields = ["id", "role", "content", "tool_call_id", "created_at"]

    def validate_session(self, session: ChatSession) -> ChatSession:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Autenticação requerida.")
        if session.organizacao_id != getattr(user, "organizacao_id", None):
            raise serializers.ValidationError("A sessão não pertence à sua organização.")
        if session.usuario_id != getattr(user, "pk", None):
            raise serializers.ValidationError("A sessão não pertence ao usuário autenticado.")
        if not session.is_active:
            raise serializers.ValidationError("A sessão está encerrada.")
        return session


class ChatRolePermission(IsAuthenticated):
    message = "Você não tem permissão para acessar o assistente."

    def has_permission(self, request, view):  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        role = getattr(request.user, "get_tipo_usuario", None)
        return role in {"admin", "coordenador", "consultor", "root"}


class ChatRateThrottle(SimpleRateThrottle):
    scope = "ai_chat"

    def get_cache_key(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class ChatSessionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [ChatRolePermission]

    def get_queryset(self):
        user = self.request.user
        return ChatSession.objects.filter(
            organizacao_id=getattr(user, "organizacao_id", None),
            usuario=user,
        )

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user, organizacao=self.request.user.organizacao)


class ChatMessageViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    ALLOWED_TOOLS_BY_ROLE = {
        "admin": set(TOOL_WRAPPERS.keys()),
        "root": set(TOOL_WRAPPERS.keys()),
        "coordenador": set(TOOL_WRAPPERS.keys()),
        "consultor": {
            "get_future_events_context",
            "get_organizacao_description",
            "get_organizacao_nucleos_context",
        },
    }
    HEAVY_TOOLS = {
        "get_membership_totals",
        "get_event_status_totals",
        "get_monthly_members",
        "get_nucleo_metrics",
    }

    serializer_class = ChatMessageSerializer
    permission_classes = [ChatRolePermission]
    throttle_classes = [ChatRateThrottle]

    def get_queryset(self):
        user = self.request.user
        return ChatMessage.objects.filter(
            organizacao_id=getattr(user, "organizacao_id", None), session__usuario=user
        )

    def _get_user_role(self) -> str:
        role = getattr(self.request.user, "get_tipo_usuario", "") or ""
        return str(role)

    def _get_allowed_tools(self, role: str) -> set[str]:
        return self.ALLOWED_TOOLS_BY_ROLE.get(role, set())

    def _filter_tool_definitions(self, role: str) -> list[dict[str, Any]]:
        allowed = self._get_allowed_tools(role)
        return [tool for tool in _build_tool_definitions() if tool["function"]["name"] in allowed]

    def _build_tool_cache_key(self, name: str, args: dict[str, Any]) -> str:
        version = get_cache_version(f"ai_chat_tool_{name}")
        args_payload = json.dumps(args, sort_keys=True, default=str)
        hashed_args = hashlib.md5(args_payload.encode()).hexdigest()
        return f"ai_chat_tool_{name}_v{version}_{hashed_args}"

    def _get_client(self) -> OpenAI:
        settings = get_ai_chat_settings()
        return OpenAI(api_key=settings.api_key, timeout=settings.request_timeout)

    def _call_openai(self, client: OpenAI, *, phase: str, session: ChatSession, **kwargs):
        start = time.monotonic()
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception:
            duration = time.monotonic() - start
            chat_openai_latency_seconds.labels(phase=phase).observe(duration)
            chat_openai_errors_total.labels(phase=phase).inc()
            logger.exception(
                "Erro ao chamar OpenAI",
                extra={
                    "phase": phase,
                    "session_id": str(session.pk),
                    "user_id": str(getattr(session.usuario, "pk", "")),
                },
            )
            raise

        duration = time.monotonic() - start
        chat_openai_latency_seconds.labels(phase=phase).observe(duration)
        logger.info(
            "Chamada ao OpenAI concluída",
            extra={
                "phase": phase,
                "session_id": str(session.pk),
                "user_id": str(getattr(session.usuario, "pk", "")),
                "duration_ms": round(duration * 1000, 2),
            },
        )
        return response

    def _build_session_context(self, session: ChatSession) -> dict[str, str]:
        organizacao = session.organizacao
        return {
            "role": "system",
            "content": (
                "Contexto da organização atual: utilize sempre os dados desta organização ao "
                "responder ou chamar ferramentas. "
                f"ID da organização: {organizacao.pk}. Nome: {organizacao.nome}."
            ),
        }

    def _serialize_history(self, session: ChatSession) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = [SYSTEM_MESSAGE, self._build_session_context(session)]
        for msg in session.messages.all():
            payload: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.role == ChatMessage.Role.ASSISTANT:
                try:
                    assistant_content = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    assistant_content = None

                if isinstance(assistant_content, dict) and assistant_content.get("tool_calls"):
                    payload = {
                        "role": msg.role,
                        "content": assistant_content.get("content", ""),
                        "tool_calls": assistant_content.get("tool_calls", []),
                    }

            if msg.tool_call_id:
                payload["tool_call_id"] = msg.tool_call_id
            serialized.append(payload)
        return serialized

    def _execute_tool_calls(
        self,
        tool_calls: Iterable[Any],
        session: ChatSession,
        assistant_message_content: str,
        role: str,
    ) -> tuple[list[dict[str, Any]], list[ChatMessage]]:
        history_messages: list[dict[str, Any]] = [
            {
                "role": "assistant",
                "content": assistant_message_content or "",
                "tool_calls": [call.model_dump() for call in tool_calls],
            }
        ]
        stored_messages: list[ChatMessage] = [
            ChatMessage.objects.create(
                session=session,
                organizacao=session.organizacao,
                role=ChatMessage.Role.ASSISTANT,
                content=json.dumps(
                    {
                        "content": assistant_message_content,
                        "tool_calls": [call.model_dump() for call in tool_calls],
                    }
                ),
            )
        ]
        for call in tool_calls:
            args = {}
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            args.setdefault("organizacao_id", str(session.organizacao_id))
            function = TOOL_WRAPPERS.get(call.function.name)
            allowed_tools = self._get_allowed_tools(role)
            if call.function.name not in allowed_tools:
                result = {"error": "Você não tem permissão para usar esta função."}
            elif not function:
                result = {"error": f"Função {call.function.name} não suportada."}
            else:
                cache_key = None
                result = None
                if call.function.name in self.HEAVY_TOOLS:
                    cache_key = self._build_tool_cache_key(call.function.name, args)
                    cached = cache.get(cache_key)
                    if cached is not None:
                        result = cached

                if result is None:
                    start = time.monotonic()
                    try:
                        result = function(**args)
                    except Exception:  # pragma: no cover - logging/edge
                        chat_tool_errors_total.labels(function=call.function.name).inc()
                        logger.exception(
                            "Erro ao executar ferramenta interna",  # pragma: no cover - logging/edge
                            extra={
                                "function": call.function.name,
                                "session_id": str(session.pk),
                                "user_id": str(getattr(session.usuario, "pk", "")),
                            },
                        )
                        result = {"error": "Não foi possível concluir a operação solicitada."}
                    finally:
                        duration = time.monotonic() - start
                        chat_tool_latency_seconds.labels(function=call.function.name).observe(duration)

                sanitized_result = _sanitize_json_value(result)

                if cache_key and result is not None:
                    cache.set(cache_key, sanitized_result, 300)

            history_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(sanitized_result),
                }
            )
            stored_messages.append(
                ChatMessage.objects.create(
                    session=session,
                    organizacao=session.organizacao,
                    role=ChatMessage.Role.TOOL,
                    content=json.dumps(sanitized_result),
                    tool_call_id=call.id,
                )
            )

        return history_messages, stored_messages

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session: ChatSession = serializer.validated_data["session"]
        user_message_text: str = serializer.validated_data["message"]

        session = get_object_or_404(
            ChatSession, pk=session.pk, organizacao=request.user.organizacao, usuario=request.user
        )

        role = self._get_user_role()
        if role not in self.ALLOWED_TOOLS_BY_ROLE:
            raise PermissionDenied("Seu perfil não tem acesso ao assistente no momento.")
        try:
            user_message = ChatMessage.objects.create(
                session=session,
                organizacao=session.organizacao,
                role=ChatMessage.Role.USER,
                content=user_message_text,
            )

            history = self._serialize_history(session)
            history.append({"role": "user", "content": user_message_text})

            client = self._get_client()
            settings = get_ai_chat_settings()
            tools = self._filter_tool_definitions(role)

            try:
                first_response = self._call_openai(
                    client,
                    phase="analysis",
                    session=session,
                    model=settings.model,
                    messages=history,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=settings.max_output_tokens,
                )
            except Exception:
                return Response(
                    {
                        "detail": "Não foi possível gerar uma resposta agora. Tente novamente em instantes.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            assistant_message = first_response.choices[0].message
            stored_tool_messages: list[ChatMessage] = []
            history_extensions: list[dict[str, Any]] = []

            if assistant_message.tool_calls:
                history_extensions, stored_tool_messages = self._execute_tool_calls(
                    assistant_message.tool_calls,
                    session,
                    assistant_message.content or "",
                    role,
                )
            elif assistant_message.content:
                history_extensions = [{"role": "assistant", "content": assistant_message.content}]

            final_history = history + history_extensions

            try:
                final_response = self._call_openai(
                    client,
                    phase="final",
                    session=session,
                    model=settings.model,
                    messages=final_history,
                    tools=tools,
                    tool_choice="none",
                    max_tokens=settings.max_output_tokens,
                )
            except Exception:
                return Response(
                    {
                        "detail": "Não foi possível finalizar a resposta agora. Tente novamente em breve.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            final_message = final_response.choices[0].message

            stored_messages = [user_message, *stored_tool_messages]
            assistant_db_message = ChatMessage.objects.create(
                session=session,
                organizacao=session.organizacao,
                role=ChatMessage.Role.ASSISTANT,
                content=final_message.content or "",
            )
            stored_messages.append(assistant_db_message)

            output = {
                "session": ChatSessionSerializer(session, context=self.get_serializer_context()).data,
                "messages": ChatMessageSerializer(stored_messages, many=True, context=self.get_serializer_context()).data,
            }
            headers = self.get_success_headers(serializer.data)
            return Response(output, status=status.HTTP_201_CREATED, headers=headers)
        except PermissionDenied:
            raise
        except Exception:
            logger.exception(
                "Erro inesperado ao processar mensagem do chat",
                extra={"session_id": str(session.pk), "user_id": str(getattr(request.user, "pk", ""))},
            )
            return Response(
                {"detail": "Ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
