import pytest
from django.test import RequestFactory
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.models import Nucleo, ParticipacaoNucleo
from nucleos.templatetags.nucleo_tags import can_request_nucleacao
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_can_request_nucleacao_allows_nucleado_without_participation(rf: RequestFactory):
    organizacao = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=organizacao)
    user = UserFactory(
        user_type=UserType.NUCLEADO.value,
        organizacao=organizacao,
        nucleo_obj=nucleo,
    )
    request = rf.get("/")
    request.user = user

    assert can_request_nucleacao({"request": request}, nucleo) is True


@pytest.mark.django_db
def test_can_request_nucleacao_blocks_nucleado_with_active_participation(rf: RequestFactory):
    organizacao = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=organizacao)
    user = UserFactory(
        user_type=UserType.NUCLEADO.value,
        organizacao=organizacao,
        nucleo_obj=nucleo,
    )
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, status="ativo")
    request = rf.get("/")
    request.user = user

    assert can_request_nucleacao({"request": request}, nucleo) is False


@pytest.mark.django_db
def test_nucleado_sees_nucleacao_cta_in_list(client):
    organizacao = OrganizacaoFactory()
    nucleo = NucleoFactory(
        organizacao=organizacao,
        classificacao=Nucleo.Classificacao.CONSTITUIDO,
    )
    user = UserFactory(
        user_type=UserType.NUCLEADO.value,
        organizacao=organizacao,
        nucleo_obj=nucleo,
    )
    client.force_login(user)

    response = client.get(reverse("nucleos:list"))

    assert "Quero ser nucleado" in response.content.decode()
