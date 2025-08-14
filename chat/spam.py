from __future__ import annotations

import re
from datetime import timedelta
from typing import Iterable

from django.utils import timezone

from .models import ChatChannel, ChatMessage, User


class SpamDetector:
    """Simple heuristics-based spam detector."""

    suspicious_domains: Iterable[str] = (".ru", ".cn", ".xyz")

    def __init__(self, messages_per_minute: int = 20, repeat_limit: int = 3, link_limit: int = 3):
        self.messages_per_minute = messages_per_minute
        self.repeat_limit = repeat_limit
        self.link_limit = link_limit

    url_re = re.compile(r"https?://\S+")

    def contains_suspicious_links(self, content: str) -> bool:
        links = self.url_re.findall(content)
        if len(links) > self.link_limit:
            return True
        return any(any(dom in link for dom in self.suspicious_domains) for link in links)

    def is_spam(self, user: User, channel: ChatChannel, content: str) -> bool:
        now = timezone.now()
        minute_ago = now - timedelta(minutes=1)
        recent = ChatMessage.objects.filter(remetente=user, channel=channel, created_at__gte=minute_ago)
        if recent.count() >= self.messages_per_minute:
            return True
        if recent.filter(conteudo=content).count() >= self.repeat_limit:
            return True
        if self.contains_suspicious_links(content):
            return True
        return False
