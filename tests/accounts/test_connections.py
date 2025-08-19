import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_aceitar_conexao(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(other)

    client.force_login(user)
    url = reverse("accounts:aceitar_conexao", args=[other.id])
    resp = client.post(url)
    assert resp.status_code == 302
    assert user.connections.filter(id=other.id).exists()
    assert not user.followers.filter(id=other.id).exists()


@pytest.mark.django_db
def test_recusar_conexao(client):
    user = User.objects.create_user(email="a@example.com", username="a", password="x")
    other = User.objects.create_user(email="b@example.com", username="b", password="x")
    user.followers.add(other)

    client.force_login(user)
    url = reverse("accounts:recusar_conexao", args=[other.id])
    resp = client.post(url)
    assert resp.status_code == 302
    assert not user.connections.filter(id=other.id).exists()
    assert not user.followers.filter(id=other.id).exists()
