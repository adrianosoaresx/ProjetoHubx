import pytest
from django.contrib.admin.sites import AdminSite
from django.db import connection

from configuracoes.admin import ConfiguracaoContaLogAdmin
from configuracoes.models import ConfiguracaoContaLog

pytestmark = pytest.mark.django_db


class DummyRequest:
    pass


def test_ip_user_agent_encrypted(admin_user):
    log = ConfiguracaoContaLog.objects.create(
        user=admin_user,
        campo="tema",
        valor_antigo="claro",
        valor_novo="escuro",
        ip="1.2.3.4",
        user_agent="ua",
    )
    with connection.cursor() as cur:
        cur.execute(
            "SELECT ip, user_agent FROM configuracoes_configuracaocontalog WHERE id=%s",
            [log.id],
        )
        raw_ip, raw_ua = cur.fetchone()
    assert raw_ip != "1.2.3.4"
    assert raw_ua != "ua"


def test_admin_decrypts(admin_user):
    log = ConfiguracaoContaLog.objects.create(
        user=admin_user,
        campo="tema",
        valor_antigo="claro",
        valor_novo="escuro",
        ip="5.6.7.8",
        user_agent="ua2",
    )
    ma = ConfiguracaoContaLogAdmin(ConfiguracaoContaLog, AdminSite())
    assert ma.ip_descriptografado(log) == "5.6.7.8"
    assert ma.user_agent_descriptografado(log) == "ua2"
