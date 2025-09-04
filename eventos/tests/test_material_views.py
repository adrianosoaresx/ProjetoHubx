import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from eventos.models import MaterialDivulgacaoEvento
from accounts.models import UserType


@pytest.mark.django_db
def test_material_list_shows_only_approved(client):
    evento = EventoFactory()
    arquivo1 = SimpleUploadedFile("file1.txt", b"x")
    MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="Aprovado",
        descricao="",
        tipo="banner",
        arquivo=arquivo1,
        status="aprovado",
    )
    arquivo2 = SimpleUploadedFile("file2.txt", b"x")
    MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="Rascunho",
        descricao="",
        tipo="banner",
        arquivo=arquivo2,
        status="criado",
    )
    user = UserFactory(user_type=UserType.ASSOCIADO, organizacao=evento.organizacao, nucleo_obj=None)
    client.force_login(user)
    resp = client.get(reverse("eventos:material_list"))
    assert resp.status_code == 200
    assert "agenda/material_list.html" in [t.name for t in resp.templates]
    materiais = list(resp.context["materiais"])
    assert len(materiais) == 1
    assert materiais[0].titulo == "Aprovado"
