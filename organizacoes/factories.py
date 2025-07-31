import factory
from factory.django import DjangoModelFactory
from .models import Organizacao


class OrganizacaoFactory(DjangoModelFactory):
    class Meta:
        model = Organizacao

    nome = factory.Faker("company", locale="pt_BR")
    descricao = factory.Faker("catch_phrase", locale="pt_BR")
    cnpj = factory.Faker("bothify", text="##.###.###/####-##", locale="pt_BR")
    slug = factory.Sequence(lambda n: f"org-{n}")
    tipo = factory.Iterator(["ong", "empresa", "coletivo"])
    rua = factory.Faker("street_name", locale="pt_BR")
    cidade = factory.Faker("city", locale="pt_BR")
    estado = factory.Faker("state_abbr", locale="pt_BR")
    contato_nome = factory.Faker("name", locale="pt_BR")
    contato_email = factory.Faker("email", locale="pt_BR")
    contato_telefone = factory.Faker("phone_number", locale="pt_BR")
