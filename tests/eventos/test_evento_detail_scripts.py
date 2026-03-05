import os
from datetime import timedelta

import django
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from accounts.models import UserType
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


User = get_user_model()


def _create_organizacao() -> Organizacao:
    return Organizacao.objects.create(nome="Org", cnpj="12345678000195")


def _create_user(organizacao: Organizacao, username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="senha123",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


def _create_evento(organizacao: Organizacao, **kwargs) -> Evento:
    inicio = timezone.now() + timedelta(days=2)
    defaults = {
        "titulo": "Evento",
        "slug": f"evento-{timezone.now().timestamp()}",
        "descricao": "Descricao",
        "data_inicio": inicio,
        "data_fim": inicio + timedelta(hours=2),
        "local": "Local",
        "cidade": "Cidade",
        "estado": "SP",
        "cep": "12345-678",
        "organizacao": organizacao,
        "status": Evento.Status.ATIVO,
        "publico_alvo": 0,
        "gratuito": True,
        "participantes_maximo": 10,
    }
    defaults.update(kwargs)
    return Evento.objects.create(**defaults)


@pytest.mark.django_db
def test_evento_detail_includes_carousel_module_script_when_inscritos_section_is_available() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "admin_evento_scripts")
    evento = _create_evento(organizacao, slug="evento-scripts")
    InscricaoEvento.all_objects.create(user=usuario, evento=evento, status="confirmada")

    client = Client()
    client.force_login(usuario)
    response = client.get(reverse("eventos:evento_detalhe", kwargs={"pk": evento.pk}))

    assert response.status_code == 200
    assert response.context["pode_ver_inscritos"] is True
    assert 'src="/static/js/carousel.js"' in response.content.decode()
