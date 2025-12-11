from datetime import datetime, timedelta

import pytest
from django.test import override_settings
from django.urls import include, path, reverse
from django.utils.http import urlencode
from django.utils.timezone import make_aware
from django.views.i18n import JavaScriptCatalog

from accounts.models import User, UserType
from eventos.forms import PublicInviteEmailForm
from eventos.models import Convite, Evento
from organizacoes.models import Organizacao


urlpatterns = [
    path("", include(("core.urls", "core"), namespace="core")),
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("eventos/", include(("eventos.urls", "eventos"), namespace="eventos")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path(
        "configuracoes/",
        include(("configuracoes.urls", "configuracoes"), namespace="configuracoes"),
    ),
    path("nucleos/", include(("nucleos.urls", "nucleos"), namespace="nucleos")),
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("conexoes/", include(("conexoes.urls", "conexoes"), namespace="conexoes")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("portfolio/", include(("portfolio.urls", "portfolio"), namespace="portfolio")),
    path("membros/", include(("membros.urls", "membros"), namespace="membros")),
    path(
        "organizacoes/",
        include(("organizacoes.urls", "organizacoes"), namespace="organizacoes"),
    ),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),
    path(
        "notificacoes/",
        include(("notificacoes.urls", "notificacoes"), namespace="notificacoes"),
    ),
]

pytestmark = pytest.mark.django_db


def _criar_convite_publico():
    organizacao = Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")
    evento = Evento.objects.create(
        titulo="Evento Público",
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
    convite = Convite.objects.create(
        evento=evento,
        publico_alvo="Todos",
        data_inicio=evento.data_inicio.date(),
        data_fim=evento.data_fim.date(),
        local=evento.local,
        cidade=evento.cidade,
        estado=evento.estado,
    )
    url = reverse("eventos:convite_public", args=[convite.short_code])
    return convite, evento, url


@override_settings(ROOT_URLCONF="eventos.tests.test_convite_public_view")
def test_convite_public_get_exibe_formulario(client):
    convite, _, url = _criar_convite_publico()

    response = client.get(url)

    assert response.status_code == 200
    assert isinstance(response.context["form"], PublicInviteEmailForm)
    assert "name=\"email\"" in response.content.decode()


@override_settings(ROOT_URLCONF="eventos.tests.test_convite_public_view")
def test_convite_public_post_email_existente_redireciona_login(client):
    convite, evento, url = _criar_convite_publico()
    user = User.objects.create_user(
        username="usuario",
        email="usuario@example.com",
        password="12345",
        organizacao=evento.organizacao,
        user_type=UserType.NUCLEADO,
    )

    response = client.post(url, {"email": user.email})

    inscricao_url = reverse("eventos:inscricao_criar", args=[evento.pk])
    expected_login = f"{reverse('accounts:login')}?{urlencode({'next': inscricao_url})}"
    assert response.status_code == 302
    assert response["Location"] == expected_login


@override_settings(ROOT_URLCONF="eventos.tests.test_convite_public_view")
def test_convite_public_post_email_novo_redireciona_registro(client):
    convite, evento, url = _criar_convite_publico()
    novo_email = "novo@example.com"

    response = client.post(url, {"email": novo_email})

    expected_register = f"{reverse('tokens:token')}?{urlencode({'evento': evento.pk})}"
    assert response.status_code == 302
    assert response["Location"] == expected_register

    session = client.session
    assert session["email"] == novo_email
