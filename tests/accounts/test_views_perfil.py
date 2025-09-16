import pytest
from django.test.utils import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _use_project_urls():
    with override_settings(ROOT_URLCONF="Hubx.urls"):
        yield


def _login_and_get_info_partial(client, user, params=None):
    client.force_login(user)
    url = reverse("accounts:perfil_info_partial")
    params = params or {}
    return client.get(url, params)


def test_perfil_info_partial_renders_biografia(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="pass123",
    )
    user.biografia = "Minha bio"
    user.save(update_fields=["biografia"])

    response = _login_and_get_info_partial(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Minha bio" in content


def test_perfil_info_partial_falls_back_to_legacy_bio(client, django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(
        email="legacy@example.com",
        username="legacy",
        password="pass123",
    )
    user.biografia = ""
    user.save(update_fields=["biografia"])

    monkeypatch.setattr(
        django_user_model,
        "bio",
        property(lambda self: "Bio antiga" if self.pk == user.pk else ""),
        raising=False,
    )

    response = _login_and_get_info_partial(client, user)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Bio antiga" in content


def test_perfil_info_section_edit_renders_form(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="owner@example.com",
        username="owner",
        password="pass123",
    )

    client.force_login(user)

    response = client.get(
        reverse("accounts:perfil"),
        {"section": "info", "info_view": "edit"},
    )

    assert response.status_code == 200
    assert response.context["perfil_default_section"] == "info"

    default_url = response.context["perfil_default_url"]
    assert default_url == reverse("accounts:perfil_sections_info")
    assert "info_view" not in default_url

    ajax_response = client.get(default_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert ajax_response.status_code == 200
    content = ajax_response.content.decode()
    assert "Informações do perfil" in content
    assert any(
        template.name and template.name.endswith("info_form.html")
        for template in getattr(ajax_response, "templates", [])
    )

