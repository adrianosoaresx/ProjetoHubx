import pytest
from django.test.utils import override_settings
from django.urls import reverse

from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory

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


def test_admin_can_access_edit_form_for_other_user(client, django_user_model):
    organizacao = OrganizacaoFactory()
    admin = django_user_model.objects.create_user(
        email="admin@example.com",
        username="admin",
        password="pass123",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
        is_staff=True,
    )
    target = django_user_model.objects.create_user(
        email="target@example.com",
        username="target",
        password="pass123",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
        contato="Usuário alvo",
    )

    client.force_login(admin)
    response = client.get(
        reverse("accounts:perfil_sections_info"),
        {"public_id": str(target.public_id)},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert str(target.public_id) in content
    assert "Você está editando o perfil" in content


def test_operator_can_update_other_user_profile(client, django_user_model):
    organizacao = OrganizacaoFactory()
    operator = django_user_model.objects.create_user(
        email="operator@example.com",
        username="operator",
        password="pass123",
        user_type=UserType.OPERADOR,
        organizacao=organizacao,
    )
    target = django_user_model.objects.create_user(
        email="member@example.com",
        username="member",
        password="pass123",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
        contato="Membro",
    )

    client.force_login(operator)
    url = reverse("accounts:perfil_sections_info")
    data = {
        "contato": "Perfil Atualizado",
        "username": target.username,
        "email": target.email,
        "cpf": target.cpf or "",
        "cnpj": target.cnpj or "",
        "razao_social": target.razao_social or "",
        "nome_fantasia": target.nome_fantasia or "",
        "biografia": target.biografia or "",
        "phone_number": target.phone_number.as_e164 if getattr(target, "phone_number", None) else "",
        "whatsapp": target.whatsapp or "",
        "birth_date": target.birth_date.isoformat() if target.birth_date else "",
        "endereco": target.endereco or "",
        "cidade": target.cidade or "",
        "estado": target.estado or "",
        "cep": target.cep or "",
        "facebook": "",
        "twitter": "",
        "instagram": "",
        "linkedin": "",
        "public_id": str(target.public_id),
    }

    response = client.post(url, data)

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.contato == "Perfil Atualizado"


def test_admin_cannot_manage_user_from_other_organization(client, django_user_model):
    org_a = OrganizacaoFactory()
    org_b = OrganizacaoFactory()
    admin = django_user_model.objects.create_user(
        email="admin@example.com",
        username="admin",
        password="pass123",
        user_type=UserType.ADMIN,
        organizacao=org_a,
        is_staff=True,
    )
    outsider = django_user_model.objects.create_user(
        email="outsider@example.com",
        username="outsider",
        password="pass123",
        user_type=UserType.ASSOCIADO,
        organizacao=org_b,
        is_associado=True,
    )

    client.force_login(admin)
    response = client.get(
        reverse("accounts:perfil_sections_info"),
        {"public_id": str(outsider.public_id)},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 403
