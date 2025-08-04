from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse

from dashboard.services import DashboardService

pytestmark = pytest.mark.django_db


def test_admin_view_invokes_service_methods(client, admin_user):
    cache.clear()
    with patch.object(
        DashboardService,
        "calcular_crescimento",
        return_value={"total": 0, "crescimento": 0.0},
    ) as spy:
        client.force_login(admin_user)
        client.get(reverse("dashboard:admin"))
        assert spy.call_count == 6

