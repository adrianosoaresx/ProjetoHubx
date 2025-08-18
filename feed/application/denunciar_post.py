from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

from feed.models import Flag, ModeracaoPost, Post


@dataclass
class DenunciarPost:
    """Registra denúncia de um post e atualiza moderação."""

    def execute(self, post: Post, user) -> None:
        if Flag.objects.filter(post=post, user=user).exists():
            raise ValidationError("Usuário já denunciou este post")
        Flag.objects.create(post=post, user=user)
        limit = getattr(settings, "FEED_FLAGS_LIMIT", 3)
        if Flag.objects.filter(post=post).count() >= limit:
            moderacao = post.moderacao
            if not moderacao or moderacao.status != "pendente":
                ModeracaoPost.objects.create(
                    post=post,
                    status="pendente",
                    motivo="Limite de denúncias atingido",
                )
