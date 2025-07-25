import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory

from .models import Empresa


class EmpresaFactory(DjangoModelFactory):
    class Meta:
        model = Empresa

    usuario = factory.SubFactory(UserFactory)
    organizacao = factory.SubFactory(OrganizacaoFactory)
    nome = factory.Faker("company", locale="pt_BR")
    cnpj = factory.Faker("cnpj", locale="pt_BR")
    tipo = factory.Iterator(["mei", "ltda", "sa"])
    municipio = factory.Faker("city", locale="pt_BR")
    estado = factory.Faker("state_abbr", locale="pt_BR")
    descricao = factory.Faker("sentence", locale="pt_BR")
    palavras_chave = factory.Faker("word", locale="pt_BR")
