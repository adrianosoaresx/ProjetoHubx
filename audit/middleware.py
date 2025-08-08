from __future__ import annotations

from asgiref.sync import async_to_sync
from django.http import HttpRequest, HttpResponse
from sentry_sdk import capture_exception

from .services import hash_ip, log_audit_async


class AuditMiddleware:
    """Middleware that logs dashboard requests for auditing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        try:
            if request.path.startswith("/dashboard"):
                user = request.user if request.user.is_authenticated else None
                ip = request.META.get("REMOTE_ADDR", "")
                metadata = (
                    request.GET.dict() if request.method == "GET" else request.POST.dict()
                )
                status = (
                    "SUCCESS" if 200 <= response.status_code < 400 else "FAILURE"
                )
                action = f"{request.method}:{request.path}"
                async_to_sync(log_audit_async)(
                    user=user,
                    action=action,
                    object_type=None,
                    object_id=None,
                    ip_hash=hash_ip(ip),
                    status=status,
                    metadata=metadata,
                )
        except Exception as exc:  # pragma: no cover - não impactar o usuário
            capture_exception(exc)
        return response
