import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

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
