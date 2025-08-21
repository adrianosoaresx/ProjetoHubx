import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory

from accounts.factories import UserFactory
from accounts.models import UserType


pytestmark = pytest.mark.django_db


def _render_for(user):
    request = RequestFactory().get("/")
    request.user = user
    return render_to_string("financeiro/aportes_form.html", {"centros": []}, request=request)


def test_aportes_form_shows_internal_for_admin():
    user = UserFactory(user_type=UserType.ADMIN)
    html = _render_for(user)
    assert 'value="aporte_externo" checked' in html
    assert 'value="aporte_interno"' in html


def test_aportes_form_hides_internal_for_non_admin():
    user = UserFactory(user_type=UserType.ASSOCIADO)
    html = _render_for(user)
    assert 'value="aporte_externo" checked' in html
    assert 'value="aporte_interno"' not in html
