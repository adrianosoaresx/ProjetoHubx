import factory
from factory.django import DjangoModelFactory
from .models import Nucleo
from organizacoes.factories import OrganizacaoFactory

class NucleoFactory(DjangoModelFactory):
    class Meta:
        model = Nucleo

    organizacao = factory.SubFactory(OrganizacaoFactory)
    nome = factory.Faker("word", locale="pt_BR")
    descricao = factory.Faker("sentence", locale="pt_BR")
