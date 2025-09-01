import pytest
from datetime import datetime, timedelta
from django.urls import reverse, path, include
from django.utils.timezone import make_aware
from django.test import override_settings

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


urlpatterns = [
    path("", include(("core.urls", "core"), namespace="core")),
    path("agenda/", include(("agenda.urls", "agenda"), namespace="agenda")),
]

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="agenda.tests.test_qrcode")
def test_usuario_ve_qrcode_apos_inscricao(client, monkeypatch):
    monkeypatch.setattr(
        InscricaoEvento,
        "gerar_qrcode",
        lambda self: setattr(self, "qrcode_url", "/fake-qrcode.png"),
    )
    organizacao = Organizacao.objects.create(
        nome="Org Teste", cnpj="00000000000191"
    )
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
        coordenador=usuario,
        organizacao=organizacao,
        status=0,
        publico_alvo=0,
        numero_convidados=10,
        numero_presentes=0,
    )

    url = reverse("agenda:evento_subscribe", args=[evento.pk])
    response = client.post(url, follow=True)

    assert response.status_code == 200
    inscricao = InscricaoEvento.objects.get(user=usuario, evento=evento)
    assert inscricao.status == "confirmada"
    assert inscricao.qrcode_url
    assert inscricao.qrcode_url in response.content.decode()

