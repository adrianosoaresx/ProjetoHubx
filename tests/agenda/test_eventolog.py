import pytest

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from agenda.factories import EventoFactory
from eventos.models import InscricaoEvento, EventoLog


@pytest.mark.django_db
def test_inscricao_confirmacao_gera_log():
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    inscricao = InscricaoEvento.objects.create(user=user, evento=evento)
    inscricao.confirmar_inscricao()
    assert EventoLog.objects.filter(evento=evento, acao="inscricao_confirmada", usuario=user).exists()
