import pytest

from discussao.factories import (
    CategoriaDiscussaoFactory,
    RespostaDiscussaoFactory,
    TopicoDiscussaoFactory,
)

pytestmark = pytest.mark.django_db


def test_factories_create_objects():
    categoria = CategoriaDiscussaoFactory()
    topico = TopicoDiscussaoFactory(categoria=categoria)
    resposta = RespostaDiscussaoFactory(topico=topico)
    assert resposta.topico == topico and topico.categoria == categoria
