from rest_framework.routers import DefaultRouter

from .api import ContatoEmpresaViewSet, EmpresaViewSet

router = DefaultRouter()
router.register(r"empresas", EmpresaViewSet, basename="empresa")
router.register(
    r"empresas/(?P<empresa_pk>[^/.]+)/contatos",
    ContatoEmpresaViewSet,
    basename="contato-empresa",
)

urlpatterns = router.urls
