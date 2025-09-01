import pytest
from celery.exceptions import Retry
from unittest.mock import patch

from empresas.factories import EmpresaFactory
from empresas.models import AvaliacaoEmpresa
from empresas.tasks import notificar_responsavel


@pytest.mark.django_db
def test_notificar_responsavel_autoretry():
    empresa = EmpresaFactory()
    avaliacao = AvaliacaoEmpresa.objects.create(
        empresa=empresa, usuario=empresa.usuario, nota=5
    )

    with patch("empresas.tasks.enviar_para_usuario", side_effect=Exception("boom")):
        with patch.object(
            notificar_responsavel, "retry", wraps=notificar_responsavel.retry
        ) as retry_mock:
            with pytest.raises(Retry):
                notificar_responsavel.apply(args=[str(avaliacao.id)])

            assert retry_mock.call_count == 1
