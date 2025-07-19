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
    razao_social = factory.Faker("company", locale="pt_BR")
    nome_fantasia = factory.Faker("company_suffix", locale="pt_BR")
    cnpj = factory.Faker("cnpj", locale="pt_BR")
    ramo_atividade = factory.Faker("job", locale="pt_BR")
    endereco = factory.Faker("street_address", locale="pt_BR")
    cidade = factory.Faker("city", locale="pt_BR")
    estado = factory.Faker("state_abbr", locale="pt_BR")
    cep = factory.Faker("postcode", locale="pt_BR")
    email_corporativo = factory.Faker("company_email", locale="pt_BR")
    telefone_corporativo = factory.Faker("phone_number", locale="pt_BR")
    site = factory.Faker("url")
    rede_social = factory.Faker("url")
