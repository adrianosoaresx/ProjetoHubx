
import pytest

from discussao.models import Denuncia, TopicoDiscussao
from discussao.services import denunciar_conteudo

pytestmark = pytest.mark.django_db(transaction=True)


def test_denunciar_conteudo(admin_user, categoria):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="t",
        conteudo="c",
        autor=admin_user,
        publico_alvo=0,
    )
    denunciar_conteudo(user=admin_user, content_object=topico, motivo="spam")
    assert Denuncia.objects.count() == 1
    with pytest.raises(Exception):
        denunciar_conteudo(user=admin_user, content_object=topico, motivo="spam")
