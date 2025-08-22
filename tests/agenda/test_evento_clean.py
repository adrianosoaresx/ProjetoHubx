from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from agenda.factories import EventoFactory


@pytest.mark.django_db
def test_evento_data_fim_posterior_data_inicio():
    inicio = timezone.now()
    evento = EventoFactory.build(data_inicio=inicio, data_fim=inicio - timedelta(hours=1))
    with pytest.raises(ValidationError) as excinfo:
        evento.clean()
    assert "data_fim" in excinfo.value.message_dict


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("numero_convidados", -1),
        ("numero_presentes", -1),
        ("valor_ingresso", Decimal("-1")),
        ("orcamento", Decimal("-1")),
        ("orcamento_estimado", Decimal("-1")),
        ("valor_gasto", Decimal("-1")),
        ("participantes_maximo", -1),
    ],
)
@pytest.mark.django_db
def test_evento_campos_devem_ser_positivos(campo, valor):
    evento = EventoFactory.build(**{campo: valor})
    with pytest.raises(ValidationError) as excinfo:
        evento.clean()
    assert campo in excinfo.value.message_dict
