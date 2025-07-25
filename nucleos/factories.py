import factory
from factory.django import DjangoModelFactory

from organizacoes.factories import OrganizacaoFactory

from .models import Nucleo


class NucleoFactory(DjangoModelFactory):
    class Meta:
        model = Nucleo

    organizacao = factory.SubFactory(OrganizacaoFactory)
    nome = factory.Faker("word", locale="pt_BR")
    descricao = factory.Faker("sentence", locale="pt_BR")
