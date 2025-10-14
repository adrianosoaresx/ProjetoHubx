import pytest
from datetime import datetime, timedelta
from django.urls import reverse, path, include
from django.utils.timezone import make_aware
from django.test import override_settings
from django.views.i18n import JavaScriptCatalog

from accounts.models import User, UserType
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
