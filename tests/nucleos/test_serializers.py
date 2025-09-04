import pytest
from decimal import Decimal

from nucleos.models import Nucleo
from nucleos.serializers import NucleoSerializer
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


def test_nucleo_serializer_contains_mensalidade():
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")
    nucleo = Nucleo.objects.create(nome="N", organizacao=org, mensalidade=Decimal("10"))
    data = NucleoSerializer(nucleo).data
    assert str(data["mensalidade"]) == "10.00"


def test_nucleo_serializer_validate_mensalidade():
    org = Organizacao.objects.create(nome="Org2", cnpj="00.000.000/0002-00", slug="org2")
    serializer = NucleoSerializer(data={"organizacao": org.pk, "nome": "N", "mensalidade": -5})
    assert not serializer.is_valid()
    assert "mensalidade" in serializer.errors
