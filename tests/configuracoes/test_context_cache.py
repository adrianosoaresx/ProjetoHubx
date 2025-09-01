import uuid

import pytest
from django.core.cache import cache

from configuracoes.models import ConfiguracaoContextual
from configuracoes.services import get_configuracao_contextual

pytestmark = pytest.mark.django_db


def test_get_configuracao_contextual_cache_and_invalidation_on_save(
    admin_user, django_assert_num_queries
):
    cache.clear()
    escopo_tipo = ConfiguracaoContextual.Escopo.ORGANIZACAO
    escopo_id = str(uuid.uuid4())

    # miss and store None
    with django_assert_num_queries(1):
        assert get_configuracao_contextual(admin_user, escopo_tipo, escopo_id) is None
    # hit cached None
    with django_assert_num_queries(0):
        assert get_configuracao_contextual(admin_user, escopo_tipo, escopo_id) is None

    ctx = ConfiguracaoContextual.objects.create(
        user=admin_user, escopo_tipo=escopo_tipo, escopo_id=escopo_id, tema="escuro"
    )

    # cache invalidated on create
    with django_assert_num_queries(1):
        ctx_fetched = get_configuracao_contextual(admin_user, escopo_tipo, escopo_id)
    assert ctx_fetched.tema == "escuro"
    # cached hit
    with django_assert_num_queries(0):
        get_configuracao_contextual(admin_user, escopo_tipo, escopo_id)

    ctx.tema = "claro"
    ctx.save()
    # cache invalidated on update
    with django_assert_num_queries(1):
        updated = get_configuracao_contextual(admin_user, escopo_tipo, escopo_id)
    assert updated.tema == "claro"
    with django_assert_num_queries(0):
        get_configuracao_contextual(admin_user, escopo_tipo, escopo_id)


def test_get_configuracao_contextual_cache_invalidation_on_delete(
    admin_user, django_assert_num_queries
):
    cache.clear()
    escopo_tipo = ConfiguracaoContextual.Escopo.ORGANIZACAO
    escopo_id = str(uuid.uuid4())
    ctx = ConfiguracaoContextual.objects.create(
        user=admin_user, escopo_tipo=escopo_tipo, escopo_id=escopo_id
    )

    # prime cache
    get_configuracao_contextual(admin_user, escopo_tipo, escopo_id)
    with django_assert_num_queries(0):
        get_configuracao_contextual(admin_user, escopo_tipo, escopo_id)

    ctx.delete()
    # cache invalidated on delete
    with django_assert_num_queries(1):
        assert get_configuracao_contextual(admin_user, escopo_tipo, escopo_id) is None
    with django_assert_num_queries(0):
        assert get_configuracao_contextual(admin_user, escopo_tipo, escopo_id) is None
