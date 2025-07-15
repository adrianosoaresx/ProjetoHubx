import factory
from factory.django import DjangoModelFactory
from forum.models import Categoria, Topico
from accounts.factories import UserFactory

class CategoriaFactory(DjangoModelFactory):
    class Meta:
        model = Categoria

    nome = factory.Faker("word", locale="pt_BR")
    organizacao = factory.SubFactory("organizacoes.factories.OrganizacaoFactory")

class TopicoFactory(DjangoModelFactory):
    class Meta:
        model = Topico

    titulo = factory.Faker("sentence", locale="pt_BR")
    conteudo = factory.Faker("paragraph", locale="pt_BR")
    categoria = factory.SubFactory(CategoriaFactory)
    autor = factory.SubFactory(UserFactory)
