from __future__ import annotations

import io
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import override_settings
from django.utils import timezone
from rest_framework.settings import api_settings
from rest_framework.test import APIClient

from agenda.models import Evento
from chat.api import notify_users
from chat.models import (
    ChatAttachment,
    ChatChannel,
    ChatMessage,
    ChatModerationLog,
    ChatParticipant,
    RelatorioChatExport,
    ResumoChat,
)
from chat.throttles import UploadRateThrottle
from nucleos.models import ParticipacaoNucleo

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_list_channels_returns_only_participated(api_client: APIClient, admin_user, coordenador_user):
    c1 = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=c1, user=admin_user)
    c2 = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=c2, user=coordenador_user)
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = reverse("chat-channel-list")
    resp = api_client.get(url)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert str(c1.id) in ids
    assert str(c2.id) not in ids


def test_upload_endpoint_saves_metadata(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-upload")
    file = SimpleUploadedFile("teste.pdf", b"%PDF-1.4", content_type="application/pdf")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mime_type"] == "application/pdf"
    assert data["tamanho"] == file.size
    assert ChatAttachment.objects.filter(id=data["attachment_id"]).exists()


@override_settings(ROOT_URLCONF="chat.api_urls")
def test_create_channel_requires_permission(api_client: APIClient, associado_user):
    api_client.force_authenticate(associado_user)
    url = reverse("chat-channel-list")
    resp = api_client.post(
        url,
        {"contexto_tipo": "nucleo", "contexto_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


@override_settings(ROOT_URLCONF="chat.api_urls")
def test_create_private_channel_requires_context(api_client: APIClient, associado_user):
    api_client.force_authenticate(associado_user)
    url = reverse("chat-channel-list")
    resp = api_client.post(url, {"contexto_tipo": "privado", "titulo": "x"})
    assert resp.status_code == 400


def test_add_and_remove_participant(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    api_client.force_authenticate(admin_user)
    add_url = reverse("chat_api:chat-channel-add-participant", args=[channel.pk])
    resp = api_client.post(add_url, {"usuarios": [coordenador_user.id]})
    assert resp.status_code == 200
    assert ChatParticipant.objects.filter(channel=channel, user=coordenador_user).exists()
    remove_url = reverse("chat_api:chat-channel-remove-participant", args=[channel.pk])
    resp = api_client.post(remove_url, {"usuarios": [coordenador_user.id]})
    assert resp.status_code == 200
    assert not ChatParticipant.objects.filter(channel=channel, user=coordenador_user).exists()


@override_settings(ROOT_URLCONF="chat.api_urls")
def test_leave_channel(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    api_client.force_authenticate(coordenador_user)
    resp = api_client.post(f"/channels/{channel.pk}/leave/")
    assert resp.status_code == 200
    assert not ChatParticipant.objects.filter(channel=channel, user=coordenador_user).exists()


@override_settings(ROOT_URLCONF="chat.api_urls")
def test_leave_channel_last_admin_forbidden(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True, is_owner=True)
    api_client.force_authenticate(admin_user)
    resp = api_client.post(f"/channels/{channel.pk}/leave/")
    assert resp.status_code == 400
    assert ChatParticipant.objects.filter(channel=channel, user=admin_user).exists()


@override_settings(ROOT_URLCONF="chat.api_urls")
def test_leave_channel_admin_with_other_admin(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user, is_admin=True)
    api_client.force_authenticate(admin_user)
    resp = api_client.post(f"/channels/{channel.pk}/leave/")
    assert resp.status_code == 200
    assert not ChatParticipant.objects.filter(channel=channel, user=admin_user).exists()


def test_send_and_list_messages(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    api_client.force_authenticate(admin_user)
    list_url = f"/api/chat/channels/{channel.id}/messages/"
    resp = api_client.post(list_url, {"tipo": "text", "conteudo": "hi"})
    assert resp.status_code == 201
    msg = ChatMessage.objects.first()
    resp = api_client.get(list_url, {"desde": msg.created_at.isoformat()})
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_send_message_with_attachment(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    api_client.force_authenticate(admin_user)
    upload_url = reverse("chat_api:chat-upload")
    file = SimpleUploadedFile("a.txt", b"a", content_type="text/plain")
    resp = api_client.post(upload_url, {"file": file}, format="multipart")
    attachment_id = resp.json()["attachment_id"]
    list_url = f"/api/chat/channels/{channel.id}/messages/"
    resp = api_client.post(list_url, {"tipo": "file", "attachment_id": attachment_id})
    assert resp.status_code == 201
    msg = ChatMessage.objects.get()
    att = ChatAttachment.objects.get(id=attachment_id)
    assert att.mensagem_id == msg.id
    assert msg.arquivo.name == att.arquivo.name


def test_send_message_with_attachment_requires_owner(
    api_client: APIClient, admin_user, coordenador_user
):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    api_client.force_authenticate(admin_user)
    upload_url = reverse("chat_api:chat-upload")
    file = SimpleUploadedFile("a.txt", b"a", content_type="text/plain")
    resp = api_client.post(upload_url, {"file": file}, format="multipart")
    attachment_id = resp.json()["attachment_id"]
    api_client.force_authenticate(coordenador_user)
    list_url = f"/api/chat/channels/{channel.id}/messages/"
    resp = api_client.post(list_url, {"tipo": "file", "attachment_id": attachment_id})
    assert resp.status_code == 400
    assert "attachment_id" in resp.json()


def test_history_endpoint_returns_messages(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="a")
    ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="b")
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = reverse("chat_api:chat-channel-messages-history", args=[channel.id])
    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 2


def test_history_endpoint_filters_by_date(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    old_time = timezone.now() - timedelta(days=2)
    old_msg = ChatMessage.objects.create(
        channel=channel,
        remetente=admin_user,
        tipo="text",
        conteudo="old",
    )
    ChatMessage.objects.filter(pk=old_msg.pk).update(created_at=old_time)
    new_msg = ChatMessage.objects.create(
        channel=channel,
        remetente=admin_user,
        tipo="text",
        conteudo="new",
    )
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = reverse("chat_api:chat-channel-messages-history", args=[channel.id])
    resp = api_client.get(url, {"inicio": new_msg.created_at.isoformat()})
    assert resp.status_code == 200
    data = resp.json()
    ids = [m["id"] for m in data["messages"]]
    assert str(new_msg.id) in ids
    assert str(old_msg.id) not in ids


def test_messages_permission_denied_for_non_participant(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    api_client.force_authenticate(coordenador_user)
    url = f"/api/chat/channels/{channel.id}/messages/"
    resp = api_client.get(url)
    assert resp.status_code == 403


def test_search_messages_filters_and_permissions(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    other = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatParticipant.objects.create(channel=other, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="hello world")
    ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="image", conteudo="hello img")
    old = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="hello old")
    ChatMessage.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=2))
    ChatMessage.objects.create(channel=other, remetente=coordenador_user, tipo="text", conteudo="hello secret")
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = reverse("chat_api:chat-channel-message-search", args=[channel.id])
    recent = timezone.now() - timedelta(hours=1)
    resp = api_client.get(url, {"q": "hello", "tipo": "text", "desde": recent.isoformat()})
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()["results"]]
    assert str(msg.id) in ids
    assert str(old.id) not in ids
    assert len(ids) == 1


def test_list_resumos(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ResumoChat.objects.create(canal=channel, periodo="diario", conteudo="Resumo", detalhes={})
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-resumos", args=[channel.id])
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json()[0]["conteudo"] == "Resumo"


def test_gerar_resumo_task_creates_record(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="ola")
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-gerar-resumo", args=[channel.id])
    resp = api_client.post(url, {"periodo": "diario"})
    assert resp.status_code == 200
    assert ResumoChat.objects.filter(canal=channel, periodo="diario").exists()


def test_search_messages_date_range(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    old_msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="foo")
    ChatMessage.objects.filter(pk=old_msg.pk).update(created_at=timezone.now() - timedelta(days=5))
    recent_msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="foo bar")
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-message-search", args=[channel.id])
    params = {
        "q": "foo",
        "desde": (timezone.now() - timedelta(days=1)).isoformat(),
        "ate": timezone.now().isoformat(),
    }
    resp = api_client.get(url, params)
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()["results"]]
    assert str(recent_msg.id) in ids
    assert str(old_msg.id) not in ids


def test_history_before_returns_previous_desc(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    msgs = [
        ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo=f"m{i}")
        for i in range(30)
    ]
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-messages-history", args=[channel.id])
    resp = api_client.get(url, {"before": str(msgs[-1].id)})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 20
    assert data["messages"][0]["id"] == str(msgs[-2].id)
    assert data["messages"][-1]["id"] == str(msgs[9].id)
    assert data["has_more"] is True


def test_history_before_accepts_timestamp(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    msgs = [
        ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo=f"t{i}")
        for i in range(3)
    ]
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-messages-history", args=[channel.id])
    ts = msgs[-1].created_at.isoformat()
    resp = api_client.get(url, {"before": ts})
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()["messages"]]
    assert str(msgs[-1].id) not in ids
    assert str(msgs[-2].id) in ids


def test_pin_and_unpin_message(api_client: APIClient, admin_user, coordenador_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=coordenador_user, tipo="text", conteudo="hi")
    api_client.force_authenticate(admin_user)
    pin_url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/pin/"
    resp = api_client.post(pin_url)
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.pinned_at is not None
    unpin_url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/unpin/"
    resp2 = api_client.post(unpin_url)
    assert resp2.status_code == 200
    msg.refresh_from_db()
    assert msg.pinned_at is None


def test_react_message(api_client: APIClient, admin_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, tipo="text", conteudo="hi")
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/react/"
    resp = api_client.post(url, {"emoji": "👍"})
    assert resp.status_code == 200
    assert resp.data["reactions"]["👍"] == 1
    assert "👍" in resp.data["user_reactions"]
    # segunda chamada alterna e remove
    resp = api_client.post(url, {"emoji": "👍"})
    assert "👍" not in resp.data["reactions"]
    assert "👍" not in resp.data["user_reactions"]


def test_mark_read_message(api_client: APIClient, admin_user, coordenador_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, tipo="text", conteudo="hi")
    api_client.force_authenticate(coordenador_user)
    url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/mark-read/"
    resp = api_client.post(url)
    assert resp.status_code == 204
    msg.refresh_from_db()
    assert coordenador_user in msg.lido_por.all()


def test_edit_and_delete_message(api_client: APIClient, admin_user, coordenador_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, conteudo="hi")
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/"
    resp = api_client.patch(url, {"conteudo": "editado"})
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.conteudo == "editado"
    # Other participant cannot edit
    api_client.force_authenticate(coordenador_user)
    resp2 = api_client.patch(url, {"conteudo": "x"})
    assert resp2.status_code == 403
    # Sender deletes
    api_client.force_authenticate(admin_user)
    del_resp = api_client.delete(url)
    assert del_resp.status_code == 204
    assert not ChatMessage.objects.filter(pk=msg.pk).exists()
    assert ChatMessage.all_objects.filter(pk=msg.pk).exists()
    logs = ChatModerationLog.objects.filter(message=msg)
    assert logs.filter(action="edit").exists()
    assert logs.filter(action="remove").exists()


def test_restore_message(api_client: APIClient, admin_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user, is_admin=True)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, conteudo="orig")
    api_client.force_authenticate(admin_user)
    # edit message to create log
    edit_url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/"
    api_client.patch(edit_url, {"conteudo": "novo"})
    log = ChatModerationLog.objects.filter(message=msg, action="edit").latest("created_at")
    restore_url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/restore/"
    resp = api_client.post(restore_url, {"log_id": str(log.id)})
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.conteudo == "orig"
    assert ChatModerationLog.objects.filter(message=msg, action="edit").count() == 2


def test_flag_message_hides_and_metrics(api_client: APIClient, admin_user):
    from chat.metrics import (
        chat_mensagens_ocultadas_total,
        chat_mensagens_sinalizadas_total,
    )

    chat_mensagens_sinalizadas_total.labels(canal_tipo="privado")._value.set(0)
    chat_mensagens_ocultadas_total._value.set(0)
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    other1 = User.objects.create_user(email="o1@x.com", username="o1", password="x")
    other2 = User.objects.create_user(email="o2@x.com", username="o2", password="x")
    other3 = User.objects.create_user(email="o3@x.com", username="o3", password="x")
    for u in (other1, other2, other3):
        ChatParticipant.objects.create(channel=conv, user=u)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, tipo="text", conteudo="hi")
    url = f"/api/chat/channels/{conv.id}/messages/{msg.id}/flag/"
    api_client.force_authenticate(other1)
    resp1 = api_client.post(url)
    assert resp1.status_code == 200 and resp1.json()["flags"] == 1
    dup = api_client.post(url)
    assert dup.status_code == 409
    api_client.force_authenticate(other2)
    api_client.post(url)
    api_client.force_authenticate(other3)
    api_client.post(url)
    msg.refresh_from_db()
    assert msg.hidden_at is not None
    assert chat_mensagens_sinalizadas_total.labels(canal_tipo="privado")._value.get() == 3
    assert chat_mensagens_ocultadas_total._value.get() == 1


def test_notifications_list_and_read(api_client: APIClient, admin_user, coordenador_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, tipo="text", conteudo="hi")
    notify_users(conv, msg)
    api_client.force_authenticate(coordenador_user)
    url = reverse("chat_api:chat-notificacao-list")
    resp = api_client.get(url)
    assert resp.status_code == 200 and resp.json()[0]["lido"] is False
    notif_id = resp.json()[0]["id"]
    read_url = reverse("chat_api:chat-notificacao-ler", args=[notif_id])
    resp2 = api_client.post(read_url)
    assert resp2.status_code == 200 and resp2.json()["lido"] is True


def test_export_channel(api_client: APIClient, admin_user):
    from chat.metrics import chat_exportacoes_total

    chat_exportacoes_total.labels(formato="json")._value.set(0)
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user, is_admin=True)
    ChatMessage.objects.create(channel=conv, remetente=admin_user, conteudo="hi")
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = reverse("chat_api:chat-channel-export", args=[conv.id]) + "?formato=json"
    resp = api_client.get(url)
    assert resp.status_code == 202
    rel = RelatorioChatExport.objects.get(channel=conv)
    assert rel.status == "concluido"
    assert chat_exportacoes_total.labels(formato="json")._value.get() == 1


def test_export_requires_permission(api_client: APIClient, associado_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=associado_user)
    api_client.force_authenticate(associado_user)
    url = reverse("chat_api:chat-channel-export", args=[conv.id])
    resp = api_client.get(url)
    assert resp.status_code == 403


def test_moderacao_endpoints(api_client: APIClient, admin_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    u1 = User.objects.create_user(email="u1@x.com", username="u1", password="x")
    u2 = User.objects.create_user(email="u2@x.com", username="u2", password="x")
    u3 = User.objects.create_user(email="u3@x.com", username="u3", password="x")
    for u in (u1, u2, u3):
        ChatParticipant.objects.create(channel=conv, user=u)
    msg1 = ChatMessage.objects.create(channel=conv, remetente=u1, conteudo="oi")
    msg2 = ChatMessage.objects.create(channel=conv, remetente=u1, conteudo="tchau")
    url1 = f"/api/chat/channels/{conv.id}/messages/{msg1.id}/flag/"
    url2 = f"/api/chat/channels/{conv.id}/messages/{msg2.id}/flag/"
    for user in (u1, u2, u3):
        api_client.force_authenticate(user)
        api_client.post(url1)
        api_client.post(url2)
    api_client.force_authenticate(admin_user)
    list_url = reverse("chat_api:chat-flags")
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    approve_url = reverse("chat_api:chat-moderacao-approve", args=[msg1.id])
    resp_a = api_client.post(approve_url)
    assert resp_a.status_code == 200
    msg1.refresh_from_db()
    assert msg1.hidden_at is None and msg1.flags.count() == 0
    remove_url = reverse("chat_api:chat-moderacao-remove", args=[msg2.id])
    resp_r = api_client.post(remove_url)
    assert resp_r.status_code == 204
    assert not ChatMessage.objects.filter(pk=msg2.pk).exists()
    assert ChatMessage.all_objects.filter(pk=msg2.pk).exists()


def test_criar_item_evento(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="x")
    perm = Permission.objects.get(codename="add_evento")
    admin_user.user_permissions.add(perm)
    api_client.force_authenticate(admin_user)
    url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/criar-item/"
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    resp = api_client.post(
        url,
        {
            "tipo": "evento",
            "titulo": "Reunião",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        },
    )
    assert resp.status_code == 201
    evento = Evento.objects.get(mensagem_origem=msg)
    assert evento.titulo == "Reunião"
    assert ChatModerationLog.objects.filter(message=msg, action="create_item").exists()


def test_criar_item_evento_sem_permissao(api_client: APIClient, associado_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=associado_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=associado_user, tipo="text", conteudo="x")
    api_client.force_authenticate(associado_user)
    url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/criar-item/"
    resp = api_client.post(url, {"tipo": "evento", "titulo": "A"})
    assert resp.status_code == 403


def test_criar_item_evento_dados_invalidos(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="x")
    perm = Permission.objects.get(codename="add_evento")
    admin_user.user_permissions.add(perm)
    api_client.force_authenticate(admin_user)
    url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/criar-item/"
    resp = api_client.post(url, {"tipo": "evento", "titulo": ""})
    assert resp.status_code == 400


def test_criar_item_tarefa(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="x")
    perm = Permission.objects.get(codename="add_tarefa")
    admin_user.user_permissions.add(perm)
    api_client.force_authenticate(admin_user)
    url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/criar-item/"
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    resp = api_client.post(
        url,
        {
            "tipo": "tarefa",
            "titulo": "Tarefa",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        },
    )
    assert resp.status_code == 201
    from agenda.models import Tarefa

    tarefa = Tarefa.objects.get(mensagem_origem=msg)
    assert tarefa.titulo == "Tarefa"
    assert ChatModerationLog.objects.filter(message=msg, action="create_item").exists()


def test_criar_item_tarefa_sem_permissao(api_client: APIClient, associado_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=associado_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=associado_user, tipo="text", conteudo="x")
    api_client.force_authenticate(associado_user)
    url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/criar-item/"
    resp = api_client.post(url, {"tipo": "tarefa", "titulo": "A"})
    assert resp.status_code == 403


def test_criar_item_tarefa_dados_invalidos(api_client: APIClient, admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="x")
    perm = Permission.objects.get(codename="add_tarefa")
    admin_user.user_permissions.add(perm)
    api_client.force_authenticate(admin_user)
    url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/criar-item/"
    resp = api_client.post(url, {"tipo": "tarefa", "titulo": ""})
    assert resp.status_code == 400

def test_upload_throttling(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    cache.clear()
    url = reverse("chat_api:chat-upload")
    original = api_settings.DEFAULT_THROTTLE_RATES.copy()
    api_settings.DEFAULT_THROTTLE_RATES["chat_upload"] = "2/minute"
    UploadRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
    try:
        for i in range(2):
            file_obj = io.BytesIO(b"data")
            file_obj.name = f"f{i}.txt"
            resp = api_client.post(url, {"file": file_obj}, format="multipart")
            assert resp.status_code == 200
        file_obj = io.BytesIO(b"data")
        file_obj.name = "f2.txt"
        resp = api_client.post(url, {"file": file_obj}, format="multipart")
        assert resp.status_code == 429
    finally:
        api_settings.DEFAULT_THROTTLE_RATES = original
        UploadRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
