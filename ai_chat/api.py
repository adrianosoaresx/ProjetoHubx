from __future__ import annotations

import json
from typing import Any, Iterable

from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from ai_chat.settings import get_ai_chat_settings
from openai import OpenAI

from .models import ChatMessage, ChatSession
from . import services as chat_services


SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "Você é um assistente que utiliza ferramentas para responder com dados atualizados "
        "da organização. Utilize as funções disponíveis quando necessário e responda em "
        "português."
    ),
}


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


class ChatRateThrottle(SimpleRateThrottle):
    scope = "ai_chat"

    def get_cache_key(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class ChatSessionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatSession.objects.filter(
            organizacao_id=getattr(user, "organizacao_id", None),
            usuario=user,
        )

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user, organizacao=self.request.user.organizacao)


class ChatMessageViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatRateThrottle]

    def get_queryset(self):
        user = self.request.user
        return ChatMessage.objects.filter(
            organizacao_id=getattr(user, "organizacao_id", None), session__usuario=user
        )

    def _get_client(self) -> OpenAI:
        settings = get_ai_chat_settings()
        return OpenAI(api_key=settings.api_key, timeout=settings.request_timeout)

    def _serialize_history(self, messages: Iterable[ChatMessage]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = [SYSTEM_MESSAGE]
        for msg in messages:
            payload: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_call_id:
                payload["tool_call_id"] = msg.tool_call_id
            serialized.append(payload)
        return serialized

    def _execute_tool_calls(
        self,
        tool_calls: Iterable[Any],
        session: ChatSession,
        assistant_message_content: str,
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
            if not function:
                result = {"error": f"Função {call.function.name} não suportada."}
            else:
                try:
                    result = function(**args)
                except Exception as exc:  # pragma: no cover - logging/edge
                    result = {"error": str(exc)}

            history_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )
            stored_messages.append(
                ChatMessage.objects.create(
                    session=session,
                    organizacao=session.organizacao,
                    role=ChatMessage.Role.TOOL,
                    content=json.dumps(result),
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

        user_message = ChatMessage.objects.create(
            session=session,
            organizacao=session.organizacao,
            role=ChatMessage.Role.USER,
            content=user_message_text,
        )

        history = self._serialize_history(session.messages.all())
        history.append({"role": "user", "content": user_message_text})

        client = self._get_client()
        settings = get_ai_chat_settings()
        tools = _build_tool_definitions()

        first_response = client.chat.completions.create(
            model=settings.model,
            messages=history,
            tools=tools,
            tool_choice="auto",
            max_tokens=settings.max_output_tokens,
        )

        assistant_message = first_response.choices[0].message
        stored_tool_messages: list[ChatMessage] = []
        history_extensions: list[dict[str, Any]] = []

        if assistant_message.tool_calls:
            history_extensions, stored_tool_messages = self._execute_tool_calls(
                assistant_message.tool_calls,
                session,
                assistant_message.content or "",
            )
        elif assistant_message.content:
            history_extensions = [
                {"role": "assistant", "content": assistant_message.content, "tool_calls": []}
            ]

        final_history = history + history_extensions

        final_response = client.chat.completions.create(
            model=settings.model,
            messages=final_history,
            tools=tools,
            tool_choice="none",
            max_tokens=settings.max_output_tokens,
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
