import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_home_anonymous(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Criar conta" in html
    assert "Entrar" in html


@pytest.mark.django_db
def test_home_authenticated(client):
    user = User.objects.create_user(username="u", email="u@example.com", password="pass")
    client.force_login(user)
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Dashboard" in html or "Ir para Dashboard" in html


@pytest.mark.django_db
def test_static_pages(client):
    for name in ["about", "terms", "privacy"]:
        resp = client.get(reverse(f"core:{name}"))
        assert resp.status_code == 200
