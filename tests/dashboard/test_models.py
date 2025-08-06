from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from dashboard.models import DashboardFilter

pytestmark = pytest.mark.django_db


def test_timestamp_fields(admin_user):
    filtro = DashboardFilter.objects.create(user=admin_user, nome="f1", filtros={})
    assert filtro.created is not None
    assert filtro.modified is not None
    assert filtro.publico is False


def test_soft_delete(admin_user):
    filtro = DashboardFilter.objects.create(user=admin_user, nome="f1", filtros={})
    filtro_id = filtro.id
    filtro.delete()

    assert not DashboardFilter.objects.filter(id=filtro_id).exists()
    deleted = DashboardFilter.all_objects.get(id=filtro_id)
    assert deleted.deleted is True
    assert deleted.deleted_at is not None


def test_non_admin_cannot_save_public_filter(cliente_user):
    filtro = DashboardFilter(user=cliente_user, nome="f1", filtros={}, publico=True)
    with pytest.raises(ValidationError):
        filtro.full_clean()
