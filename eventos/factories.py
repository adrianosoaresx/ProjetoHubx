from datetime import timedelta, timezone as dt_timezone

import factory
from factory.django import DjangoModelFactory, FileField

from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

from .models import Evento


class EventoFactory(DjangoModelFactory):
    class Meta:
        model = Evento

    organizacao = factory.SubFactory(OrganizacaoFactory)
    nucleo = factory.SubFactory(NucleoFactory, organizacao=factory.SelfAttribute("..organizacao"))
    titulo = factory.Faker("sentence", locale="pt_BR")
    descricao = factory.Faker("paragraph", locale="pt_BR")
    data_inicio = factory.Faker("future_datetime", tzinfo=dt_timezone.utc)
    data_fim = factory.LazyAttribute(lambda o: o.data_inicio + timedelta(hours=1))
    local = factory.Faker("street_address", locale="pt_BR")
    cidade = factory.Faker("city", locale="pt_BR")
    estado = factory.Faker("state_abbr", locale="pt_BR")
    cep = factory.Faker("postcode", locale="pt_BR")
    status = factory.Faker("random_element", elements=[0, 1, 2, 3])
    publico_alvo = factory.Faker("random_element", elements=[0, 1, 2])
    participantes_maximo = factory.Faker("pyint", min_value=10, max_value=100)
    numero_presentes = factory.LazyAttribute(
        lambda o: (o.participantes_maximo or 0) // 2
    )
    valor_associado = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    valor_nucleado = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    cronograma = factory.Faker("paragraph", locale="pt_BR")
    informacoes_adicionais = factory.Faker("paragraph", locale="pt_BR")
    briefing = FileField(
        filename="briefing.pdf",
        data=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n",
        content_type="application/pdf",
    )
    parcerias = FileField(
        filename="parcerias.pdf",
        data=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n",
        content_type="application/pdf",
    )
