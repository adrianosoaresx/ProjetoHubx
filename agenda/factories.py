from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from organizacoes.factories import OrganizacaoFactory

from .models import Evento


class EventoFactory(DjangoModelFactory):
    class Meta:
        model = Evento

    organizacao = factory.SubFactory(OrganizacaoFactory)
    titulo = factory.Faker("sentence", locale="pt_BR")
    descricao = factory.Faker("paragraph", locale="pt_BR")
    data_inicio = factory.Faker("future_datetime", tzinfo=timezone.utc)
    data_fim = factory.LazyAttribute(lambda o: o.data_inicio + timedelta(hours=1))
