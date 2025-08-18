from rest_framework.routers import DefaultRouter

from .api import (
    CategoriaDiscussaoViewSet,
    DenunciaViewSet,
    RespostaViewSet,
    TagViewSet,
    TopicoViewSet,
    VotoDiscussaoViewSet,
)

router = DefaultRouter()
router.register(r"discussao/categorias", CategoriaDiscussaoViewSet, basename="categoria")
router.register(r"discussao/tags", TagViewSet, basename="tag")
router.register(r"discussao/topicos", TopicoViewSet, basename="topico")
router.register(r"discussao/respostas", RespostaViewSet, basename="resposta")
router.register(r"discussao/votos", VotoDiscussaoViewSet, basename="voto")
router.register(r"discussao/denuncias", DenunciaViewSet, basename="denuncia")

urlpatterns = router.urls
