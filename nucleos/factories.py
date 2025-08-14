import factory
from factory.django import DjangoModelFactory

from organizacoes.factories import OrganizacaoFactory

from .models import Nucleo


class NucleoFactory(DjangoModelFactory):
    class Meta:
        model = Nucleo

    organizacao = factory.SubFactory(OrganizacaoFactory)
    nome = factory.Sequence(lambda n: f"nucleo{n}")
    descricao = factory.Faker("sentence", locale="pt_BR")
