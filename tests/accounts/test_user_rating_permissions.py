import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.forms import UserRatingForm
from accounts.models import UserRating
from organizacoes.models import Organizacao


@pytest.mark.django_db
def test_perfil_avaliar_allows_same_organization(client, django_user_model):
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
    rater = django_user_model.objects.create_user(
        email="rater@example.com",
        username="rater",
        password="pass",
        organizacao=org,
    )
    target = django_user_model.objects.create_user(
        email="target@example.com",
        username="target",
        password="pass",
        organizacao=org,
    )

    client.force_login(rater)
    response = client.post(
        reverse("accounts:perfil_avaliar", args=[target.public_id]),
        {"score": 5, "comment": "Great"},
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 201
    assert UserRating.objects.filter(rated_by=rater, rated_user=target).exists()


@pytest.mark.django_db
def test_perfil_avaliar_blocks_different_organization(client, django_user_model):
    org1 = Organizacao.objects.create(nome="Org 1", cnpj="00.000.000/0001-00")
    org2 = Organizacao.objects.create(nome="Org 2", cnpj="00.000.000/0002-00")
    rater = django_user_model.objects.create_user(
        email="rater@example.com",
        username="rater",
        password="pass",
        organizacao=org1,
    )
    target = django_user_model.objects.create_user(
        email="target@example.com",
        username="target",
        password="pass",
        organizacao=org2,
    )

    client.force_login(rater)
    response = client.post(
        reverse("accounts:perfil_avaliar", args=[target.public_id]),
        {"score": 3, "comment": "Ok"},
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 403
    assert not UserRating.objects.filter(rated_by=rater, rated_user=target).exists()
    assert "sua organização" in response.json().get("detail", "")


@pytest.mark.django_db
def test_perfil_avaliar_blocks_self_rating(client, django_user_model):
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
    user = django_user_model.objects.create_user(
        email="self@example.com",
        username="self",
        password="pass",
        organizacao=org,
    )

    client.force_login(user)
    response = client.post(
        reverse("accounts:perfil_avaliar", args=[user.public_id]),
        {"score": 4, "comment": "Self"},
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 403
    assert not UserRating.objects.filter(rated_by=user, rated_user=user).exists()
    assert "próprio" in response.json().get("detail", "")


@pytest.mark.django_db
def test_user_rating_form_requires_same_organization(django_user_model):
    org1 = Organizacao.objects.create(nome="Org 1", cnpj="00.000.000/0001-00")
    org2 = Organizacao.objects.create(nome="Org 2", cnpj="00.000.000/0002-00")
    rater = django_user_model.objects.create_user(
        email="rater@example.com",
        username="rater",
        password="pass",
        organizacao=org1,
    )
    target = django_user_model.objects.create_user(
        email="target@example.com",
        username="target",
        password="pass",
        organizacao=org2,
    )

    form = UserRatingForm(
        data={"score": 4, "comment": "Nice"}, user=rater, rated_user=target
    )

    assert not form.is_valid()
    assert "sua organização" in " ".join(form.non_field_errors())


@pytest.mark.django_db
def test_user_rating_model_validation_requires_same_organization(django_user_model):
    org1 = Organizacao.objects.create(nome="Org 1", cnpj="00.000.000/0001-00")
    org2 = Organizacao.objects.create(nome="Org 2", cnpj="00.000.000/0002-00")
    rater = django_user_model.objects.create_user(
        email="rater@example.com",
        username="rater",
        password="pass",
        organizacao=org1,
    )
    target = django_user_model.objects.create_user(
        email="target@example.com",
        username="target",
        password="pass",
        organizacao=org2,
    )

    rating = UserRating(rated_user=target, rated_by=rater, score=5, comment="Nice")

    with pytest.raises(ValidationError) as excinfo:
        rating.full_clean_with_user(rater)

    assert "sua organização" in " ".join(
        excinfo.value.message_dict.get("__all__", [])
        + excinfo.value.message_dict.get("non_field_errors", [])
    )
