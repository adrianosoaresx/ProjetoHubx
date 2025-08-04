from __future__ import annotations

import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ApiToken


class ApiTokenAuthentication(BaseAuthentication):
    """Autenticação via header ``Authorization: Bearer <token>``."""

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        raw_token = auth_header.split(" ", 1)[1]
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            api_token = ApiToken.objects.get(token_hash=token_hash, revoked_at__isnull=True)
        except ApiToken.DoesNotExist as exc:  # pragma: no cover - branch
            raise AuthenticationFailed("Token inválido ou revogado") from exc
        if api_token.expires_at and api_token.expires_at <= timezone.now():
            raise AuthenticationFailed("Token expirado")
        api_token.last_used_at = timezone.now()
        api_token.save(update_fields=["last_used_at"])
        return (api_token.user, api_token)
