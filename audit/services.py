from __future__ import annotations

import hashlib
from typing import Any

from asgiref.sync import sync_to_async
from prometheus_client import Counter
from sentry_sdk import capture_exception

from .models import AuditLog

AUDIT_LOG_TOTAL = Counter(
    "audit_log_total", "Total de logs de auditoria por ação", ["action"]
)

_SENSITIVE_KEYS = {"password", "token", "cpf", "secret"}


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


def sanitize_metadata(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k.lower() not in _SENSITIVE_KEYS}


def _create_log(
    user: Any,
    action: str,
    object_type: str | None,
    object_id: str | None,
    ip_hash: str,
    status: str,
    metadata: dict[str, Any],
) -> None:
    AuditLog.objects.create(
        user=user,
        action=action,
        object_type=object_type or "",
        object_id=object_id or "",
        ip_hash=ip_hash,
        status=status,
        metadata=sanitize_metadata(metadata),
    )
    AUDIT_LOG_TOTAL.labels(action=action).inc()


async def log_audit_async(
    user: Any,
    action: str,
    object_type: str | None = None,
    object_id: str | None = None,
    ip_hash: str = "",
    status: str = AuditLog.Status.SUCCESS,
    metadata: dict[str, Any] | None = None,
) -> None:
    if metadata is None:
        metadata = {}
    try:
        await sync_to_async(_create_log)(
            user, action, object_type, object_id, ip_hash, status, metadata
        )
    except Exception as exc:  # pragma: no cover - segurança
        capture_exception(exc)


def log_audit(
    user: Any,
    action: str,
    object_type: str | None = None,
    object_id: str | None = None,
    ip_hash: str = "",
    status: str = AuditLog.Status.SUCCESS,
    metadata: dict[str, Any] | None = None,
) -> None:
    if metadata is None:
        metadata = {}
    try:
        _create_log(user, action, object_type, object_id, ip_hash, status, metadata)
    except Exception as exc:  # pragma: no cover - segurança
        capture_exception(exc)
