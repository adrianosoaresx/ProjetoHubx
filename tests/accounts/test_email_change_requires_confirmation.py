import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_email_change_generates_confirmation_token(client):
    user = User.objects.create_user(
        email="old@example.com",
        username="u",
        password="123",
        cpf="123.456.789-00",
    )
    client.force_login(user)
    resp = client.post(
        reverse("accounts:informacoes_pessoais"),
        {
            "nome_completo": "Nome",
            "username": "u",
            "email": "new@example.com",
            "cpf": "123.456.789-00",
            "biografia": "",
            "fone": "",
            "whatsapp": "",
            "endereco": "",
            "cidade": "",
            "estado": "",
            "cep": "",
        },
    )
    assert resp.status_code == 302
    user.refresh_from_db()
    assert not user.is_active
    assert not user.email_confirmed
    assert AccountToken.objects.filter(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        used_at__isnull=True,
    ).exists()
