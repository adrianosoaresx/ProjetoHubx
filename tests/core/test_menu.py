from typing import Optional

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from accounts.models import UserType
from core.menu import MenuItem, build_menu


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
        (UserType.ASSOCIADO, {"associados": False, "tokens": False}),
        (UserType.COORDENADOR, {"associados": False, "tokens": False}),
        (UserType.ADMIN, {"associados": True, "tokens": True}),
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

    if user_type is UserType.ADMIN:
        user.is_staff = True
        user.save(update_fields=["is_staff"])

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
@pytest.mark.parametrize(
    ("user_type", "expected_url_name"),
    [
        (UserType.ADMIN, "dashboard:admin_dashboard_admin"),
        (UserType.OPERADOR, "dashboard:admin_dashboard_admin"),
        (UserType.ASSOCIADO, "dashboard:associado_dashboard"),
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
