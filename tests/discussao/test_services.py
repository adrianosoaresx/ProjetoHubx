
import pytest
from django.utils import timezone

from discussao.models import Denuncia, TopicoDiscussao
from discussao.services import denunciar_conteudo, verificar_prazo_edicao

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


def test_verificar_prazo_edicao_autor(nucleado_user, categoria):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="t",
        conteudo="c",
        autor=nucleado_user,
        publico_alvo=0,
    )
    assert verificar_prazo_edicao(topico, nucleado_user)


@pytest.mark.parametrize("user_fixture", ["admin_user", "root_user"])
def test_verificar_prazo_edicao_admin_root(request, user_fixture, nucleado_user, categoria):
    user = request.getfixturevalue(user_fixture)
    topico = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="t",
        conteudo="c",
        autor=nucleado_user,
        publico_alvo=0,
    )
    topico.created_at = timezone.now() - timezone.timedelta(minutes=30)
    topico.save(update_fields=["created_at"])
    assert verificar_prazo_edicao(topico, user)


def test_verificar_prazo_edicao_prazo_expirado(nucleado_user, categoria):
    topico = TopicoDiscussao.objects.create(
        categoria=categoria,
        titulo="t",
        conteudo="c",
        autor=nucleado_user,
        publico_alvo=0,
    )
    topico.created_at = timezone.now() - timezone.timedelta(minutes=30)
    topico.save(update_fields=["created_at"])
    assert not verificar_prazo_edicao(topico, nucleado_user)
