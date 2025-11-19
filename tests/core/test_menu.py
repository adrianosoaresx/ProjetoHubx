from typing import Optional

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from accounts.models import UserType
from core.menu import MenuItem, build_menu
from organizacoes.models import Organizacao


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("user_type", "expected_children"),
    [
        (UserType.ASSOCIADO, ["child_assoc"]),
        (UserType.ADMIN, ["child_admin"]),
    ],
)
def test_build_menu_filters_nested_items(monkeypatch, user_type, expected_children):
    def _fake_menu():
        return [
            MenuItem(
                id="parent",
                path="/parent/",
                label="Parent",
                icon="icon",
                permissions=[UserType.ADMIN.value, UserType.ASSOCIADO.value],
                children=[
                    MenuItem(
                        id="child_assoc",
                        path="/child-assoc/",
                        label="Associado",
                        icon="icon",
                        permissions=[UserType.ASSOCIADO.value],
                    ),
                    MenuItem(
                        id="child_admin",
                        path="/child-admin/",
                        label="Admin",
                        icon="icon",
                        permissions=[UserType.ADMIN.value],
                    ),
                ],
            )
        ]

    monkeypatch.setattr("core.menu._get_menu_items", _fake_menu)

    user_model = get_user_model()
    user = user_model.objects.create_user(
        email=f"{user_type.value}@example.com",
        username=f"{user_type.value}",
        password="test-pass",
        user_type=user_type,
    )

    request = RequestFactory().get("/parent/")
    request.user = user

    menu = build_menu(request)

    assert len(menu) == 1
    child_ids = [child.id for child in menu[0].children or []]
    assert child_ids == expected_children


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("user_type", "expected_visibility"),
    [
        (
            UserType.ASSOCIADO,
            {
                "membros": False,
                "tokens": False,
                "nucleos": True,
                "eventos": True,
                "feed": True,
                "notificacoes_templates": False,
            },
        ),
        (
            UserType.COORDENADOR,
            {
                "membros": False,
                "tokens": False,
                "nucleos": True,
                "eventos": True,
                "feed": True,
                "notificacoes_templates": False,
            },
        ),
        (
            UserType.ADMIN,
            {
                "membros": True,
                "tokens": False,
                "nucleos": True,
                "eventos": True,
                "feed": True,
                "notificacoes_templates": True,
            },
        ),
        (
            UserType.ROOT,
            {
                "membros": False,
                "tokens": False,
                "nucleos": False,
                "eventos": False,
                "feed": False,
                "notificacoes_templates": True,
            },
        ),
    ],
)
def test_main_menu_visibility_by_user_type(user_type, expected_visibility):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email=f"{user_type.value}-menu@example.com",
        username=f"{user_type.value}_menu",
        password="test-pass",
        user_type=user_type,
    )

    if user_type in {UserType.ADMIN, UserType.ROOT}:
        user.is_staff = True
        update_fields = ["is_staff"]
        if user_type is UserType.ROOT:
            user.is_superuser = True
            update_fields.append("is_superuser")
        user.save(update_fields=update_fields)

    request = RequestFactory().get("/")
    request.user = user

    menu = build_menu(request)

    def _get_item(item_id: str) -> Optional[MenuItem]:
        for item in menu:
            if item.id == item_id:
                return item
        return None

    for item_id, should_exist in expected_visibility.items():
        item = _get_item(item_id)
        if should_exist:
            assert item is not None, f"{item_id} should be visible for {user_type.value}"
        else:
            assert item is None, f"{item_id} should be hidden for {user_type.value}"

    if expected_visibility.get("tokens"):
        tokens_item = _get_item("tokens")
        assert tokens_item is not None
        child_ids = {child.id for child in tokens_item.children or []}
        assert {"tokens_gerar", "tokens_listar"} <= child_ids


@pytest.mark.django_db
def test_consultor_can_view_nucleos_eventos_and_feed():
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="consultor-menu@example.com",
        username="consultor_menu",
        password="test-pass",
        user_type=UserType.CONSULTOR,
    )

    request = RequestFactory().get("/")
    request.user = user

    menu = build_menu(request)
    menu_ids = {item.id for item in menu}

    assert {"nucleos", "eventos", "feed"} <= menu_ids


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("user_type", "expected_url_name"),
    [
        (UserType.ADMIN, "dashboard:admin_dashboard_admin"),
        (UserType.OPERADOR, "dashboard:admin_dashboard_admin"),
        (UserType.ASSOCIADO, "dashboard:membro_dashboard"),
        (UserType.COORDENADOR, "dashboard:coordenador_dashboard"),
        (UserType.NUCLEADO, "dashboard:membro_dashboard"),
        (UserType.CONSULTOR, "dashboard:consultor_dashboard"),
    ],
)
def test_dashboard_menu_points_to_role_specific_view(user_type, expected_url_name):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email=f"{user_type.value}-dashboard@example.com",
        username=f"{user_type.value}_dashboard",
        password="test-pass",
        user_type=user_type,
    )

    request = RequestFactory().get("/")
    request.user = user

    menu = build_menu(request)

    dashboard_item = next(item for item in menu if item.id == "admin-dashboard")

    assert dashboard_item.path == reverse(expected_url_name)


@pytest.mark.django_db
def test_dashboard_visible_for_legacy_membro_user():
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="legacy-membro@example.com",
        username="legacy_membro",
        password="test-pass",
        user_type=UserType.CONVIDADO,
        is_associado=True,
    )

    assert user.get_tipo_usuario == UserType.ASSOCIADO.value

    request = RequestFactory().get("/")
    request.user = user

    menu = build_menu(request)

    dashboard_item = next((item for item in menu if item.id == "admin-dashboard"), None)

    assert dashboard_item is not None
    assert dashboard_item.path == reverse("dashboard:membro_dashboard")


@pytest.mark.django_db
def test_dashboard_visible_for_consultor_user_type_instance(monkeypatch):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="consultor-enum@example.com",
        username="consultor_enum",
        password="test-pass",
        user_type=UserType.CONSULTOR,
    )

    # Simula cenário em que o tipo de usuário é retornado como enumeração
    monkeypatch.setattr(
        user.__class__,
        "get_tipo_usuario",
        property(lambda self: UserType.CONSULTOR),
    )

    request = RequestFactory().get("/")
    request.user = user

    menu = build_menu(request)

    dashboard_item = next((item for item in menu if item.id == "admin-dashboard"), None)

    assert dashboard_item is not None
    assert dashboard_item.path == reverse("dashboard:consultor_dashboard")


@pytest.mark.django_db
def test_organizacao_site_menu_opens_in_new_tab():
    organizacao = Organizacao.objects.create(
        nome="Org Hubx",
        cnpj="00.000.000/0001-90",
        nome_site="Org Oficial",
        site="https://org.example.com",
    )

    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="org-menu@example.com",
        username="org_menu",
        password="test-pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )

    request = RequestFactory().get("/")
    request.user = user

    menu = build_menu(request)

    org_site_item = next((item for item in menu if item.id == "organizacao-site"), None)

    assert org_site_item is not None
    assert org_site_item.target == "_blank"
