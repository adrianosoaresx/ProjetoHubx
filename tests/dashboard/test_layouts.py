import json
import json
import pytest
from django.urls import reverse

from dashboard.models import DashboardLayout
from organizacoes.factories import OrganizacaoFactory
from organizacoes.models import Organizacao
from accounts.models import UserType
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_layout_crud(client, admin_user):
    client.force_login(admin_user)
    resp = client.post(reverse('dashboard:layout-create'), {
        'nome': 'Meu',
        'publico': False,
        'layout_json': json.dumps(['a'])
    })
    assert resp.status_code == 302
    layout = DashboardLayout.objects.get(nome='Meu')
    resp = client.post(reverse('dashboard:layout-save', args=[layout.pk]), {'layout_json': json.dumps(['b'])})
    assert resp.status_code == 204
    layout.refresh_from_db()
    assert layout.layout_json == json.dumps(['b'])
    resp = client.post(reverse('dashboard:layout-delete', args=[layout.pk]))
    assert resp.status_code == 302
    assert DashboardLayout.objects.filter(pk=layout.pk).count() == 0


@pytest.mark.django_db
def test_layout_permission(client, admin_user, cliente_user):
    layout = DashboardLayout.objects.create(user=admin_user, nome='X', layout_json='[]')
    client.force_login(cliente_user)
    resp = client.post(reverse('dashboard:layout-save', args=[layout.pk]), {'layout_json': '[]'})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_comparativo_endpoint(client, admin_user):
    org2 = OrganizacaoFactory()
    User.objects.create_user(username='admin2', email='a2@example.com', password='pass', user_type=UserType.ADMIN, organizacao=org2)
    client.force_login(admin_user)
    url = reverse('dashboard_api:dashboard-comparativo') + '?metricas=num_users'
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert 'atual' in data and 'media' in data
    total_users = User.objects.count()
    orgs = Organizacao.objects.count()
    expected = total_users / orgs
    assert data['media']['num_users'] == pytest.approx(expected)
    assert all(not isinstance(v, dict) for v in data['media'].values())
