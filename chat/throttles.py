from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class UploadRateThrottle(SimpleRateThrottle):
    scope = "chat_upload"

    def get_cache_key(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class FlagRateThrottle(SimpleRateThrottle):
    scope = "chat_flag"

    def get_cache_key(self, request, view):  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
