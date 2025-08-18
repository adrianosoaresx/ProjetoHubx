import pytest
from django.core.exceptions import ValidationError

from dashboard.models import MetricDefinition
from dashboard.services import DashboardMetricsService

pytestmark = pytest.mark.django_db


def test_metric_definition_validation(admin_user):
    md = MetricDefinition(
        code="dyn_users",
        titulo="Usuários",
        provider="contar_usuarios",
        owner=admin_user,
    )
    md.full_clean()  # no error
    md.provider = "inexistente"
    with pytest.raises(ValidationError):
        md.full_clean()


def test_get_metrics_with_dynamic_definition(admin_user):
    MetricDefinition.objects.create(
        code="dyn_users",
        titulo="Usuários",
        provider="contar_usuarios",
        owner=admin_user,
        ativo=True,
    )
    metrics = DashboardMetricsService.get_metrics(admin_user, metricas=["dyn_users"])
    assert "dyn_users" in metrics
    assert "total" in metrics["dyn_users"]
