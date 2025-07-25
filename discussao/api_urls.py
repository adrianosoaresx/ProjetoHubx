from rest_framework.routers import DefaultRouter

from .api import RespostaViewSet, TagViewSet, TopicoViewSet

router = DefaultRouter()
router.register(r"discussao/tags", TagViewSet, basename="tag")
router.register(r"discussao/topicos", TopicoViewSet, basename="topico")
router.register(r"discussao/respostas", RespostaViewSet, basename="resposta")

urlpatterns = router.urls
