from __future__ import annotations

import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .metrics import tokens_api_tokens_used_total
from .models import ApiToken, ApiTokenIp, ApiTokenLog


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
        if api_token.user is None or getattr(api_token.user, "deleted", False):
            raise AuthenticationFailed("Usuário desativado")

        device_fingerprint = request.headers.get("X-Device-Fingerprint")
        if api_token.device_fingerprint and api_token.device_fingerprint != device_fingerprint:
            raise AuthenticationFailed("Fingerprint inválido")

        ip_address = request.META.get("REMOTE_ADDR", "")
        ip_rules = list(api_token.ips.all())
        if any(rule.tipo == ApiTokenIp.Tipo.NEGADO and rule.ip == ip_address for rule in ip_rules):
            raise AuthenticationFailed("IP bloqueado")
        allowed_ips = [rule.ip for rule in ip_rules if rule.tipo == ApiTokenIp.Tipo.PERMITIDO]
        if allowed_ips and ip_address not in allowed_ips:
            raise AuthenticationFailed("IP não permitido")

        api_token.last_used_at = timezone.now()
        api_token.save(update_fields=["last_used_at"])
        ApiTokenLog.objects.create(
            token=api_token,
            usuario=api_token.user,
            acao=ApiTokenLog.Acao.USO,
            ip=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        tokens_api_tokens_used_total.inc()
        return (api_token.user, api_token)
