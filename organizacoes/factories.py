import factory
from factory.django import DjangoModelFactory
from .models import Organizacao

class OrganizacaoFactory(DjangoModelFactory):
    class Meta:
        model = Organizacao

    nome = factory.Faker("company", locale="pt_BR")
    descricao = factory.Faker("catch_phrase", locale="pt_BR")
    cnpj = factory.Faker("bothify", text="##.###.###/####-##", locale="pt_BR")
