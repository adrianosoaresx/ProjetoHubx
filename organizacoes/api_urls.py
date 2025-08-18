from rest_framework.routers import DefaultRouter

from .api import (
    OrganizacaoEmpresaViewSet,
    OrganizacaoEventoViewSet,
    OrganizacaoNucleoViewSet,
    OrganizacaoPostViewSet,
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

urlpatterns = router.urls
