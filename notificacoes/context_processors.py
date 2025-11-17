from __future__ import annotations

from .models import Canal, NotificationLog, NotificationStatus


def push_notification_count(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"push_notification_pending_count": 0}

    count = NotificationLog.objects.filter(
        user=request.user,
        canal=Canal.PUSH,
        status=NotificationStatus.ENVIADA,
    ).count()
    return {"push_notification_pending_count": count}
