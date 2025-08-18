import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from discussao.factories import TopicoDiscussaoFactory


@pytest.mark.django_db
def test_upload_valido_png():
    user = UserFactory()
    topico = TopicoDiscussaoFactory(autor=user)
    client = APIClient()
    client.force_authenticate(user)
    arquivo = SimpleUploadedFile("f.png", b"foo", content_type="image/png")
    resp = client.post(
        reverse("discussao_api:resposta-list"),
        {"topico": topico.id, "conteudo": "ok", "arquivo": arquivo},
        format="multipart",
    )
    assert resp.status_code == 201


@pytest.mark.django_db
def test_upload_extensao_invalida():
    user = UserFactory()
    topico = TopicoDiscussaoFactory(autor=user)
    client = APIClient()
    client.force_authenticate(user)
    arquivo = SimpleUploadedFile("malware.exe", b"foo", content_type="application/octet-stream")
    resp = client.post(
        reverse("discussao_api:resposta-list"),
        {"topico": topico.id, "conteudo": "ok", "arquivo": arquivo},
        format="multipart",
    )
    assert resp.status_code == 400
    assert "Tipo de arquivo não permitido" in resp.data["arquivo"][0]


@pytest.mark.django_db
def test_upload_tamanho_excedido(settings):
    settings.DISCUSSAO_MAX_FILE_MB = 1
    user = UserFactory()
    topico = TopicoDiscussaoFactory(autor=user)
    client = APIClient()
    client.force_authenticate(user)
    big = b"x" * (1 * 1024 * 1024 + 1)
    arquivo = SimpleUploadedFile("big.pdf", big, content_type="application/pdf")
    resp = client.post(
        reverse("discussao_api:resposta-list"),
        {"topico": topico.id, "conteudo": "ok", "arquivo": arquivo},
        format="multipart",
    )
    assert resp.status_code == 400
    assert "tamanho máximo" in resp.data["arquivo"][0]
