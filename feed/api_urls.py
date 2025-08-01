from rest_framework.routers import SimpleRouter

from .api import (
    CommentViewSet,
    LikeViewSet,
    ModeracaoPostViewSet,
    PostViewSet,
)

router = SimpleRouter()
router.register(r"posts", PostViewSet, basename="post")
router.register(r"comments", CommentViewSet, basename="comment")
router.register(r"likes", LikeViewSet, basename="like")
router.register(r"moderacoes", ModeracaoPostViewSet, basename="moderacao")

urlpatterns = router.urls
