import factory
from factory.django import DjangoModelFactory
from .models import Evento
from organizacoes.factories import OrganizacaoFactory

class EventoFactory(DjangoModelFactory):
    class Meta:
        model = Evento

    organizacao = factory.SubFactory(OrganizacaoFactory)
    titulo = factory.Faker("sentence", locale="pt_BR")
    descricao = factory.Faker("paragraph", locale="pt_BR")
    data_hora = factory.Faker("date_time", locale="pt_BR")
    duracao = factory.Faker("time_delta")
    link_inscricao = factory.Faker("url")
