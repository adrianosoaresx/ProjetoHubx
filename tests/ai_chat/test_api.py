import json
import sys
import types
import json
import sys
import types
from types import SimpleNamespace

import pytest
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

# Stub do client OpenAI para evitar dependência externa durante os testes
if "openai" not in sys.modules:
    openai_module = types.ModuleType("openai")
    openai_module.OpenAI = type("FakeOpenAI", (), {})
    sys.modules["openai"] = openai_module

from accounts.factories import UserFactory
from accounts.models import UserType
from ai_chat import api
from ai_chat.models import ChatMessage, ChatSession
from organizacoes.factories import OrganizacaoFactory


class FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.type = "function"
        self.function = SimpleNamespace(name=name, arguments=arguments)

    def model_dump(self):
        return {
            "id": self.id,
            "type": self.type,
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


@pytest.mark.django_db
def test_chat_message_queryset_filters_by_organizacao():
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, user_type=UserType.ADMIN)
    other_user = UserFactory(organizacao=other_org, user_type=UserType.ADMIN)

    session = ChatSession.objects.create(usuario=user, organizacao=org)
    other_session = ChatSession.objects.create(usuario=other_user, organizacao=other_org)

    ChatMessage.objects.create(
        session=session, organizacao=org, role=ChatMessage.Role.USER, content="mensagem correta"
    )
    ChatMessage.objects.create(
        session=other_session, organizacao=other_org, role=ChatMessage.Role.USER, content="fora"
    )

    request = APIRequestFactory().get("/")
    request.user = user
    view = api.ChatMessageViewSet()
    view.request = request

    results = list(view.get_queryset().values_list("content", flat=True))

    assert results == ["mensagem correta"]


@pytest.mark.django_db
def test_chat_message_flow_executes_tool_and_returns_final_response(monkeypatch):
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, user_type=UserType.ADMIN)
    session = ChatSession.objects.create(usuario=user, organizacao=org)

    captured_calls: list[str] = []

    def fake_tool(organizacao_id: str):
        captured_calls.append(organizacao_id)
        return {"organizacao_id": organizacao_id, "totals": {"ativos": 9}}

    monkeypatch.setitem(api.TOOL_WRAPPERS, "get_membership_totals", fake_tool)

    analysis_tool_call = FakeToolCall(
        "call_1",
        "get_membership_totals",
        json.dumps({"organizacao_id": str(org.id)}),
    )
    responses = iter(
        [
            FakeResponse(SimpleNamespace(content="vou consultar", tool_calls=[analysis_tool_call])),
            FakeResponse(SimpleNamespace(content="resposta final", tool_calls=[])),
        ]
    )

    monkeypatch.setattr(api.ChatMessageViewSet, "_get_client", lambda self: object())
    monkeypatch.setattr(
        api.ChatMessageViewSet,
        "_call_openai",
        lambda self, client, *, phase, session, **kwargs: next(responses),
    )

    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("ai_chat_api:chat-message-list"),
        {"session": str(session.pk), "message": "olá"},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()

    assert captured_calls == [str(org.id)]
    roles = [message["role"] for message in data["messages"]]
    assert roles == ["user", "assistant", "tool", "assistant"]

    stored_messages = ChatMessage.objects.filter(session=session).order_by("created_at")
    assert stored_messages.count() == 4
    assert stored_messages.last().content == "resposta final"


@pytest.mark.django_db
def test_chat_role_permission_allows_associado_with_limited_tools():
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, user_type=UserType.ASSOCIADO)
    user.nucleo = None
    user.save(update_fields=["nucleo"])

    request = APIRequestFactory().get("/")
    request.user = user

    permission = api.ChatRolePermission()
    assert permission.has_permission(request, None) is True

    view = api.ChatMessageViewSet()
    allowed_tools = view._get_allowed_tools(user.get_tipo_usuario)
    assert allowed_tools == {
        "get_future_events_context",
        "get_eventos_list",
        "get_organizacao_description",
        "get_organizacao_nucleos_context",
        "get_nucleos_list",
    }


@pytest.mark.django_db
def test_chat_role_permission_blocks_unlisted_profile():
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, user_type=UserType.CONVIDADO)
    session = ChatSession.objects.create(usuario=user, organizacao=org)

    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("ai_chat_api:chat-message-list"),
        {"session": str(session.pk), "message": "olá"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_chat_message_associado_uses_only_public_tools(monkeypatch):
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, user_type=UserType.ASSOCIADO)
    user.nucleo = None
    user.save(update_fields=["nucleo"])
    session = ChatSession.objects.create(usuario=user, organizacao=org)

    collected_tools: list[set[str]] = []

    def fake_call(self, client, *, phase, session, **kwargs):
        tools = kwargs.get("tools") or []
        collected_tools.append({tool["function"]["name"] for tool in tools})
        content = "resposta final" if phase == "final" else "ok"
        return FakeResponse(SimpleNamespace(content=content, tool_calls=[]))

    monkeypatch.setattr(api.ChatMessageViewSet, "_get_client", lambda self: object())
    monkeypatch.setattr(api.ChatMessageViewSet, "_call_openai", fake_call)

    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("ai_chat_api:chat-message-list"),
        {"session": str(session.pk), "message": "olá"},
        format="json",
    )

    assert response.status_code == 201
    assert collected_tools == [
        {
            "get_future_events_context",
            "get_eventos_list",
            "get_organizacao_description",
            "get_organizacao_nucleos_context",
            "get_nucleos_list",
        },
        {
            "get_future_events_context",
            "get_eventos_list",
            "get_organizacao_description",
            "get_organizacao_nucleos_context",
            "get_nucleos_list",
        },
    ]

    data = response.json()
    assert [message["role"] for message in data["messages"]] == ["user", "assistant"]
