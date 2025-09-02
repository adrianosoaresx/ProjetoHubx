from __future__ import annotations

import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory

from .models import CategoriaDiscussao, RespostaDiscussao, TopicoDiscussao


class CategoriaDiscussaoFactory(DjangoModelFactory):
    class Meta:
        model = CategoriaDiscussao

    nome = factory.Faker("word", locale="pt_BR")
    organizacao = factory.SubFactory(OrganizacaoFactory)


class TopicoDiscussaoFactory(DjangoModelFactory):
    class Meta:
        model = TopicoDiscussao

    categoria = factory.SubFactory(CategoriaDiscussaoFactory)
    titulo = factory.Faker("sentence", locale="pt_BR")
    slug = factory.Sequence(lambda n: f"topico-{n}")
    conteudo = factory.Faker("paragraph", locale="pt_BR")
    autor = factory.SubFactory(UserFactory)
    publico_alvo = factory.Faker("random_element", elements=[0, 1, 2])


class RespostaDiscussaoFactory(DjangoModelFactory):
    class Meta:
        model = RespostaDiscussao

    topico = factory.SubFactory(TopicoDiscussaoFactory)
    autor = factory.SubFactory(UserFactory)
    conteudo = factory.Faker("sentence", locale="pt_BR")
