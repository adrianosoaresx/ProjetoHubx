from unittest.mock import patch

from django.test import TestCase

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from organizacoes.tasks import enviar_email_membros
from organizacoes import metrics


class EnviarEmailMembrosMetricsTests(TestCase):
    def setUp(self):
        self.org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=self.org)

    @patch("organizacoes.tasks.enviar_para_usuario")
    def test_enviar_email_membros_increments_metric(self, mock_enviar):
        metrics.membros_notificados_total._value.set(0)
        enviar_email_membros(self.org.id, "created")
        self.assertEqual(metrics.membros_notificados_total._value.get(), 1.0)
        mock_enviar.assert_called_once()
