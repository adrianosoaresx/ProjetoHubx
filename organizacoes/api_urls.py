from rest_framework.routers import DefaultRouter

from .api import (
    OrganizacaoEmpresaViewSet,
    OrganizacaoEventoViewSet,
    OrganizacaoCentroCustoViewSet,
    OrganizacaoNucleoViewSet,
    OrganizacaoPluginViewSet,
    OrganizacaoPostViewSet,
    OrganizacaoRecursoViewSet,
    OrganizacaoUserViewSet,
    OrganizacaoViewSet,
)

router = DefaultRouter()
router.register(r"organizacoes", OrganizacaoViewSet, basename="organizacao")
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/usuarios",
    OrganizacaoUserViewSet,
    basename="organizacao-usuarios",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/nucleos",
    OrganizacaoNucleoViewSet,
    basename="organizacao-nucleos",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/eventos",
    OrganizacaoEventoViewSet,
    basename="organizacao-eventos",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/empresas",
    OrganizacaoEmpresaViewSet,
    basename="organizacao-empresas",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/posts",
    OrganizacaoPostViewSet,
    basename="organizacao-posts",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/centros-custo",
    OrganizacaoCentroCustoViewSet,
    basename="organizacao-centros-custo",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/plugins",
    OrganizacaoPluginViewSet,
    basename="organizacao-plugins",
)
router.register(
    r"organizacoes/(?P<organizacao_pk>[^/.]+)/recursos",
    OrganizacaoRecursoViewSet,
    basename="organizacao-recursos",
)

urlpatterns = router.urls
