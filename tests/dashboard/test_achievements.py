import pytest

from agenda.models import InscricaoEvento
from agenda.factories import EventoFactory
from dashboard.models import Achievement, DashboardConfig, UserAchievement
from dashboard.services import check_achievements


@pytest.mark.django_db
def test_award_dashboard_achievement(admin_user):
    ach = Achievement.objects.get(code="5_dashboards")
    for i in range(5):
        DashboardConfig.objects.create(user=admin_user, nome=f"cfg{i}", config={})
    check_achievements(admin_user)
    assert UserAchievement.objects.filter(user=admin_user, achievement=ach).exists()


@pytest.mark.django_db
def test_award_inscricao_achievement(admin_user):
    ach = Achievement.objects.get(code="100_inscricoes")
    for _ in range(100):
        ev = EventoFactory(organizacao=admin_user.organizacao, coordenador=admin_user)
        InscricaoEvento.objects.create(user=admin_user, evento=ev)
    check_achievements(admin_user)
    assert UserAchievement.objects.filter(user=admin_user, achievement=ach).exists()
