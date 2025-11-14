from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied

from accounts.models import UserType
from rest_framework.permissions import BasePermission


ALLOWED_NOTIFICATION_TEMPLATE_ROLES = {UserType.ADMIN.value, UserType.ROOT.value}


def _resolve_user_roles(user) -> set[str]:
    roles: set[str] = set()

    raw_tipo = getattr(user, "get_tipo_usuario", None)
    if isinstance(raw_tipo, UserType):
        roles.add(raw_tipo.value)
    elif raw_tipo:
        roles.add(raw_tipo)

    raw_user_type = getattr(user, "user_type", None)
    if isinstance(raw_user_type, UserType):
        roles.add(raw_user_type.value)
    elif raw_user_type:
        roles.add(raw_user_type)

    if getattr(user, "is_superuser", False):
        roles.add(UserType.ROOT.value)

    return roles


def user_is_notification_admin(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False

    roles = _resolve_user_roles(user)
    return any(role in ALLOWED_NOTIFICATION_TEMPLATE_ROLES for role in roles)


def has_notifications_permission(user, perm: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False

    if user_is_notification_admin(user):
        return True

    return user.has_perm(perm)


def notifications_permission_required(perm: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not has_notifications_permission(request.user, perm):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class CanSendNotifications(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and (user.is_staff or user.has_perm("notificacoes.can_send_notifications")))
