import pytest

from feed.models import ModeracaoPost, Post

pytestmark = pytest.mark.django_db


def test_post_moderation(admin_user, organizacao, settings):
    settings.FEED_BAD_WORDS = ["ruim"]
    post = Post.objects.create(autor=admin_user, organizacao=organizacao, conteudo="coisa ruim")
    assert ModeracaoPost.objects.filter(post=post, status="pendente").exists()
