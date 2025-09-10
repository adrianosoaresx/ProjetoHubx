from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Union

from django.contrib.auth import get_user_model

User = get_user_model()


@dataclass
class CustomItem:
    """Representa item customizado injetado por plugin."""

    conteudo: str


class FeedPlugin(Protocol):
    """Contrato para plugins do feed."""

    def render(self, user: User) -> List[Union["Post", CustomItem]]:  # noqa: F821
        """Retorna itens extras para o feed do usuário."""
        ...
