import pytest
from django.test import override_settings
from django.urls import reverse

from configuracoes.services import atualizar_preferencias_usuario

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_locale_middleware_usa_configuracao(admin_client, admin_user):
    atualizar_preferencias_usuario(admin_user, {"idioma": "en-US"})
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.idioma == "en-US"
    resp = admin_client.get(reverse("configuracoes"))
    assert resp.wsgi_request.LANGUAGE_CODE == "en-us"
