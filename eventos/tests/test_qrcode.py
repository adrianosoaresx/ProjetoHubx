from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse, path, include

from django.core import mail
from django.core.files.storage import default_storage
from django.utils.timezone import make_aware
from django.test import override_settings
from django.views.i18n import JavaScriptCatalog

from accounts.models import User, UserType
from eventos import models as eventos_models
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


urlpatterns = [
    path("", include(("core.urls", "core"), namespace="core")),
    path("eventos/", include(("eventos.urls", "eventos"), namespace="eventos")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("notificacoes/", include(("notificacoes.urls", "notificacoes"), namespace="notificacoes")),
]

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_usuario_ve_qrcode_apos_inscricao(client, monkeypatch):
    monkeypatch.setattr(
        InscricaoEvento,
        "gerar_qrcode",
        lambda self: setattr(self, "qrcode_url", "/fake-qrcode.png"),
    )
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario",
        email="u@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    url = reverse("eventos:evento_subscribe", args=[evento.pk])
    response = client.post(url)

    assert response.status_code == 302
    inscricao = InscricaoEvento.objects.get(user=usuario, evento=evento)
    assert inscricao.status == "confirmada"
    assert inscricao.qrcode_url


@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_envia_email_com_qrcode_apos_inscricao(client, monkeypatch):
    def fake_gerar_qrcode(self):
        self.qrcode_url = "/fake-qrcode.png"
        return b"fake-qrcode-bytes"

    monkeypatch.setattr(InscricaoEvento, "gerar_qrcode", fake_gerar_qrcode)
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-email",
        email="email@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    url = reverse("eventos:evento_subscribe", args=[evento.pk])
    response = client.post(url)

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert "Inscrição confirmada" in email.subject
    assert email.to == [usuario.email]
    assert any(
        alternative[0].find("data:image/png;base64,") >= 0 for alternative in email.alternatives
    )
    assert any(att[0].endswith(".png") for att in email.attachments)


@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_usuario_cancela_inscricao_confirmada(client, monkeypatch):
    monkeypatch.setattr(
        InscricaoEvento,
        "gerar_qrcode",
        lambda self: setattr(self, "qrcode_url", "/fake-qrcode.png"),
    )
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-cancel",
        email="cancel@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])
    client.post(subscribe_url)

    response = client.post(cancel_url)

    assert response.status_code == 302
    with pytest.raises(InscricaoEvento.DoesNotExist):
        InscricaoEvento.objects.get(user=usuario, evento=evento)
    inscricao = InscricaoEvento.all_objects.get(user=usuario, evento=evento)
    assert inscricao.status == "cancelada"
    assert inscricao.deleted is True


@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_usuario_nao_cancela_inscricao_pagamento_validado(client, monkeypatch):
    monkeypatch.setattr(
        InscricaoEvento,
        "gerar_qrcode",
        lambda self: setattr(self, "qrcode_url", "/fake-qrcode.png"),
    )
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-cancel-validado",
        email="cancel-validado@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])
    client.post(subscribe_url)

    inscricao = InscricaoEvento.objects.get(user=usuario, evento=evento)
    inscricao.pagamento_validado = True
    inscricao.save(update_fields=["pagamento_validado"])

    response = client.post(cancel_url)

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.status == "confirmada"
    assert inscricao.deleted is False


def test_gerar_qrcode_inclui_dados_da_inscricao(monkeypatch):
    captured_data = {}

    class DummyImage:
        def save(self, buffer, format):
            buffer.write(b"dummy")

    def fake_make(data):
        captured_data["payload"] = data
        return DummyImage()

    monkeypatch.setattr(eventos_models.qrcode, "make", fake_make)
    monkeypatch.setattr(default_storage, "save", lambda name, content: name)
    monkeypatch.setattr(default_storage, "url", lambda path: f"/media/{path}")

    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-qrcode",
        email="usuario-qrcode@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO,
        cpf="123.456.789-00",
    )

    evento = Evento.objects.create(
        titulo="Evento com QRCode",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    inscricao = InscricaoEvento.objects.create(
        user=usuario,
        evento=evento,
        status="confirmada",
        valor_pago=Decimal("25.50"),
    )

    inscricao.gerar_qrcode()

    assert "payload" in captured_data
    payload_str = captured_data["payload"]
    assert payload_str.startswith(f"inscricao:{inscricao.pk}")

    partes = payload_str.split(":")
    assert partes[0] == "inscricao"
    assert partes[1] == str(inscricao.pk)
    if len(partes) > 2:
        assert partes[2] == InscricaoEvento.gerar_checksum(str(inscricao.pk))


@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_checkin_processa_payload_com_prefixo(client, monkeypatch):
    captured_data = {}

    class DummyImage:
        def save(self, buffer, format):
            buffer.write(b"dummy")

    def fake_make(data):
        captured_data["payload"] = data
        return DummyImage()

    monkeypatch.setattr(eventos_models.qrcode, "make", fake_make)
    monkeypatch.setattr(default_storage, "save", lambda name, content: name)
    monkeypatch.setattr(default_storage, "url", lambda path: f"/media/{path}")

    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-checkin",
        email="checkin@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento com Check-in",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    inscricao = InscricaoEvento.objects.create(
        user=usuario,
        evento=evento,
        status="confirmada",
    )

    inscricao.gerar_qrcode()

    codigo = captured_data.get("payload")
    assert codigo and codigo.startswith(f"inscricao:{inscricao.pk}")

    checkin_url = reverse("eventos:inscricao_checkin", args=[inscricao.pk])
    response = client.post(checkin_url, {"codigo": codigo})

    inscricao.refresh_from_db()
    assert response.status_code == 200
    assert inscricao.check_in_realizado_em is not None

@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_usuario_nao_cria_inscricao_duplicada(client, monkeypatch):
    monkeypatch.setattr(
        InscricaoEvento,
        "gerar_qrcode",
        lambda self: setattr(self, "qrcode_url", "/fake-qrcode.png"),
    )
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-duplicado",
        email="dup@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    url = reverse("eventos:evento_subscribe", args=[evento.pk])
    first_response = client.post(url)
    assert first_response.status_code == 302
    second_response = client.post(url)
    assert second_response.status_code == 302
    assert InscricaoEvento.objects.filter(user=usuario, evento=evento).count() == 1


@override_settings(ROOT_URLCONF="eventos.tests.test_qrcode")
def test_usuario_reinscreve_apos_cancelamento(client, monkeypatch):
    monkeypatch.setattr(
        InscricaoEvento,
        "gerar_qrcode",
        lambda self: setattr(self, "qrcode_url", "/fake-qrcode.png"),
    )
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    usuario = User.objects.create_user(
        username="usuario-reinscricao",
        email="reinscricao@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
    )
    client.force_login(usuario)

    evento = Evento.objects.create(
        titulo="Evento",
        descricao="Desc",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua 1",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
    )

    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])

    first_response = client.post(subscribe_url)
    assert first_response.status_code == 302
    inscricao = InscricaoEvento.objects.get(user=usuario, evento=evento)
    inscricao_pk = inscricao.pk

    cancel_response = client.post(cancel_url)
    assert cancel_response.status_code == 302
    inscricao_cancelada = InscricaoEvento.all_objects.get(user=usuario, evento=evento)
    assert inscricao_cancelada.deleted is True
    assert inscricao_cancelada.status == "cancelada"

    second_response = client.post(subscribe_url)
    assert second_response.status_code == 302
    inscricao_final = InscricaoEvento.objects.get(user=usuario, evento=evento)
    assert inscricao_final.pk == inscricao_pk
    assert inscricao_final.deleted is False
    assert inscricao_final.status == "confirmada"
