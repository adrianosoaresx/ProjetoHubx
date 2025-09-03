from rest_framework.routers import SimpleRouter

from .api import (
    BookmarkViewSet,
    CommentViewSet,
    PostViewSet,
    TagViewSet,
)

router = SimpleRouter()
router.register(r"posts", PostViewSet, basename="post")
router.register(r"comments", CommentViewSet, basename="comment")
router.register(r"bookmarks", BookmarkViewSet, basename="bookmark")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = router.urls
