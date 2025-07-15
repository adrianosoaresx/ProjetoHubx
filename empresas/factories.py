import factory
from factory.django import DjangoModelFactory
from .models import Empresa
from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory

class EmpresaFactory(DjangoModelFactory):
    class Meta:
        model = Empresa

    usuario = factory.SubFactory(UserFactory)
    organizacao = factory.SubFactory(OrganizacaoFactory)
    cnpj = factory.Faker("cnpj", locale="pt_BR")
    nome = factory.Faker("company", locale="pt_BR")
    tipo = factory.Faker("word", locale="pt_BR")
    municipio = factory.Faker("city", locale="pt_BR")
    estado = factory.Faker("state_abbr", locale="pt_BR")
    descricao = factory.Faker("paragraph", locale="pt_BR")
