import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import UserType
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_promover_form_get(client):
    organizacao = OrganizacaoFactory()
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="membro",
        email="membro@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    client.force_login(admin)

    url = reverse("accounts:associado_promover_form", args=[associado.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert associado.username in response.content.decode()


@pytest.mark.django_db
def test_promover_form_promove_consultor(client):
    organizacao = OrganizacaoFactory()
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="membro",
        email="membro@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    nucleo = NucleoFactory(organizacao=organizacao)

    client.force_login(admin)

    url = reverse("accounts:associado_promover_form", args=[associado.pk])
    response = client.post(
        url,
        {
            "promover_consultor": "1",
            "nucleos": [str(nucleo.pk)],
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Promoção registrada com sucesso" in content

    nucleo.refresh_from_db()
    assert nucleo.consultor_id == associado.pk

    associado.refresh_from_db()
    assert associado.user_type == UserType.CONSULTOR


@pytest.mark.django_db
def test_promover_form_promove_coordenador(client):
    organizacao = OrganizacaoFactory()
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="membro",
        email="membro@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    nucleo = NucleoFactory(organizacao=organizacao)

    client.force_login(admin)

    url = reverse("accounts:associado_promover_form", args=[associado.pk])
    papel = ParticipacaoNucleo.PapelCoordenador.MARKETING
    response = client.post(
        url,
        {
            "promover_coordenador": "1",
            "papel_coordenador": papel,
            "nucleos": [str(nucleo.pk)],
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Promoção registrada com sucesso" in content

    participacao = ParticipacaoNucleo.objects.get(user=associado, nucleo=nucleo)
    assert participacao.papel_coordenador == papel
    assert participacao.papel == "coordenador"

    associado.refresh_from_db()
    assert associado.user_type == UserType.COORDENADOR
    assert associado.is_coordenador is True


@pytest.mark.django_db
def test_promover_form_impede_selecao_simultanea(client):
    organizacao = OrganizacaoFactory()
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="membro",
        email="membro@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    nucleo = NucleoFactory(organizacao=organizacao)

    client.force_login(admin)

    url = reverse("accounts:associado_promover_form", args=[associado.pk])
    papel = ParticipacaoNucleo.PapelCoordenador.MARKETING
    response = client.post(
        url,
        {
            "promover_consultor": "1",
            "promover_coordenador": "1",
            "papel_coordenador": papel,
            "nucleos": [str(nucleo.pk)],
        },
    )

    assert response.status_code == 400
    content = response.content.decode()
    assert "Selecione apenas uma opção de promoção" in content
    nucleo.refresh_from_db()
    assert nucleo.consultor_id is None
    assert not ParticipacaoNucleo.objects.filter(user=associado, nucleo=nucleo).exists()


@pytest.mark.django_db
def test_promover_form_impede_papel_ja_ocupado(client):
    organizacao = OrganizacaoFactory()
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="novo",
        email="novo@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    ocupante = User.objects.create_user(
        username="ocupante",
        email="ocupante@example.com",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )
    nucleo = NucleoFactory(organizacao=organizacao)
    ParticipacaoNucleo.objects.create(
        user=ocupante,
        nucleo=nucleo,
        papel="coordenador",
        papel_coordenador=ParticipacaoNucleo.PapelCoordenador.MARKETING,
        status="ativo",
    )

    client.force_login(admin)
    url = reverse("accounts:associado_promover_form", args=[associado.pk])
    response = client.post(
        url,
        {
            "promover_coordenador": "1",
            "papel_coordenador": ParticipacaoNucleo.PapelCoordenador.MARKETING,
            "nucleos": [str(nucleo.pk)],
        },
    )

    assert response.status_code == 400
    content = response.content.decode()
    assert "já está ocupado" in content
    assert not ParticipacaoNucleo.objects.filter(user=associado, nucleo=nucleo).exists()


@pytest.mark.django_db
def test_promover_form_restringe_multiplos_nucleos_para_papeis_exclusivos(client):
    organizacao = OrganizacaoFactory()
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="membro",
        email="membro2@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    nucleo1 = NucleoFactory(organizacao=organizacao)
    nucleo2 = NucleoFactory(organizacao=organizacao)

    client.force_login(admin)
    url = reverse("accounts:associado_promover_form", args=[associado.pk])
    response = client.post(
        url,
        {
            "promover_coordenador": "1",
            "papel_coordenador": ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
            "nucleos": [str(nucleo1.pk), str(nucleo2.pk)],
        },
    )

    assert response.status_code == 400
    assert "apenas um núcleo" in response.content.decode()
