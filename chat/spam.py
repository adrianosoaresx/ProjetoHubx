from __future__ import annotations

import re
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import ChatChannel, User


class SpamDetector:
    """Simple heuristics-based spam detector."""

    suspicious_domains: Iterable[str] = (".ru", ".cn", ".xyz")

    def __init__(
        self,
        messages_per_minute: int | None = None,
        repeat_limit: int | None = None,
        link_limit: int | None = None,
    ):
        self.messages_per_minute = messages_per_minute or getattr(
            settings, "CHAT_SPAM_MESSAGES_PER_MINUTE", 20
        )
        self.repeat_limit = repeat_limit or getattr(
            settings, "CHAT_SPAM_REPEAT_LIMIT", 3
        )
        self.link_limit = link_limit or getattr(settings, "CHAT_SPAM_LINK_LIMIT", 3)

    url_re = re.compile(r"https?://\S+")

    def contains_suspicious_links(self, content: str) -> bool:
        links = self.url_re.findall(content)
        if len(links) > self.link_limit:
            return True
        return any(any(dom in link for dom in self.suspicious_domains) for link in links)

    def is_spam(self, user: User, channel: ChatChannel, content: str) -> bool:
        now = timezone.now()
        minute_ago = now - timedelta(minutes=1)

        # Contagem de mensagens por usuário em cache
        key = f"chat:spam:ts:{user.id}:{channel.id}"
        timestamps = cache.get(key, [])
        timestamps = [ts for ts in timestamps if ts > minute_ago]
        is_spam = len(timestamps) >= self.messages_per_minute
        timestamps.append(now)
        cache.set(key, timestamps, timeout=60)

        # Contagem de mensagens repetidas
        repeat_key = f"chat:spam:repeat:{user.id}:{channel.id}:{hash(content)}"
        repeat_count = cache.get(repeat_key, 0)
        if repeat_count >= self.repeat_limit:
            is_spam = True
        if cache.add(repeat_key, 1, timeout=60) is False:
            cache.incr(repeat_key)

        if self.contains_suspicious_links(content):
            is_spam = True

        return is_spam
