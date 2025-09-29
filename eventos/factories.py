from datetime import timedelta, timezone as dt_timezone

import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

from .models import Evento


class EventoFactory(DjangoModelFactory):
    class Meta:
        model = Evento

    organizacao = factory.SubFactory(OrganizacaoFactory)
    nucleo = factory.SubFactory(NucleoFactory, organizacao=factory.SelfAttribute("..organizacao"))
    coordenador = factory.SubFactory(UserFactory)
    titulo = factory.Faker("sentence", locale="pt_BR")
    descricao = factory.Faker("paragraph", locale="pt_BR")
    data_inicio = factory.Faker("future_datetime", tzinfo=dt_timezone.utc)
    data_fim = factory.LazyAttribute(lambda o: o.data_inicio + timedelta(hours=1))
    local = factory.Faker("street_address", locale="pt_BR")
    cidade = factory.Faker("city", locale="pt_BR")
    estado = factory.Faker("state_abbr", locale="pt_BR")
    cep = factory.Faker("postcode", locale="pt_BR")
    status = factory.Faker("random_element", elements=[0, 1, 2])
    publico_alvo = factory.Faker("random_element", elements=[0, 1, 2])
    numero_convidados = factory.Faker("pyint", min_value=10, max_value=100)
    numero_presentes = factory.LazyAttribute(lambda o: o.numero_convidados // 2)
    valor_ingresso = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    cronograma = factory.Faker("paragraph", locale="pt_BR")
    informacoes_adicionais = factory.Faker("paragraph", locale="pt_BR")
    briefing = factory.Faker("url")
    parcerias = factory.Faker("url")
    contato_nome = factory.Faker("name", locale="pt_BR")
    contato_email = factory.Faker("email", locale="pt_BR")
    contato_whatsapp = factory.Faker("msisdn")
