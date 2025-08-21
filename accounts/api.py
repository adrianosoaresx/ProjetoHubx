from __future__ import annotations

import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from audit.models import AuditLog
from audit.services import hash_ip, log_audit
from .models import AccountToken, SecurityEvent
from tokens.models import TOTPDevice
from .serializers import UserSerializer
from .tasks import (
    send_cancel_delete_email,
    send_confirmation_email,
    send_password_reset_email,
)

User = get_user_model()


class AccountViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):

        if self.action in {"delete_me", "enable_2fa", "disable_2fa", "resend_confirmation"}:

            return [IsAuthenticated()]
        return [AllowAny()]

    @action(detail=False, methods=["post"], url_path="confirm-email")
    def confirm_email(self, request):
        code = request.data.get("token")
        if not code:
            return Response({"detail": _("Token ausente.")}, status=400)
        token = get_object_or_404(AccountToken, codigo=code, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION)
        if token.expires_at < timezone.now() or token.used_at:
            return Response({"detail": _("Token inválido ou expirado.")}, status=400)
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        token.usuario.is_active = True
        token.usuario.email_confirmed = True
        token.usuario.save(update_fields=["is_active", "email_confirmed"])
        SecurityEvent.objects.create(
            usuario=token.usuario,
            evento="email_confirmado",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": _("Email confirmado.")})

    @action(detail=False, methods=["post"], url_path="resend-confirmation")
    def resend_confirmation(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"detail": _("Email ausente.")}, status=400)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(status=204)
        if user.is_active:
            return Response({"detail": _("Conta já ativada.")}, status=400)
        token = AccountToken.objects.create(
            usuario=user,
            tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
            expires_at=timezone.now() + timezone.timedelta(hours=24),
            ip_gerado=request.META.get("REMOTE_ADDR"),
        )
        send_confirmation_email.delay(token.id)
        SecurityEvent.objects.create(
            usuario=user,
            evento="resend_confirmation",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response(status=204)

    @action(detail=False, methods=["post"], url_path="request-password-reset")
    def request_password_reset(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"detail": _("Email ausente.")}, status=400)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(status=204)
        token = AccountToken.objects.create(
            usuario=user,
            tipo=AccountToken.Tipo.PASSWORD_RESET,
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            ip_gerado=request.META.get("REMOTE_ADDR"),
        )
        send_password_reset_email.delay(token.id)
        return Response(status=204)

    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        code = request.data.get("token")
        new_password = request.data.get("password")
        if not code or not new_password:
            return Response({"detail": _("Dados incompletos.")}, status=400)
        token = get_object_or_404(AccountToken, codigo=code, tipo=AccountToken.Tipo.PASSWORD_RESET)
        if token.expires_at < timezone.now() or token.used_at:
            return Response({"detail": _("Token inválido ou expirado.")}, status=400)
        user = token.usuario
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"detail": e.messages}, status=400)
        user.failed_login_attempts = 0
        user.lock_expires_at = None
        user.set_password(new_password)
        user.save(update_fields=["password", "failed_login_attempts", "lock_expires_at"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="senha_redefinida",
            ip=request.META.get("REMOTE_ADDR"),
        )
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return Response({"detail": _("Senha redefinida.")})

    @action(detail=False, methods=["post"], url_path="enable-2fa")
    def enable_2fa(self, request):
        user = request.user
        code = request.data.get("code")
        if user.two_factor_enabled:
            return Response({"detail": _("2FA já habilitado.")}, status=400)
        if not user.two_factor_secret:
            secret = pyotp.random_base32()
            user.two_factor_secret = secret
            user.save(update_fields=["two_factor_secret"])
            otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Hubx")
            return Response({"otpauth_url": otp_uri, "secret": secret})
        if not code:
            return Response({"detail": _("Código obrigatório.")}, status=400)
        if not pyotp.TOTP(user.two_factor_secret).verify(code):
            return Response({"detail": _("Código inválido.")}, status=400)
        user.two_factor_enabled = True
        user.save(update_fields=["two_factor_enabled"])
        TOTPDevice.all_objects.update_or_create(
            usuario=user,
            defaults={
                "secret": user.two_factor_secret,
                "confirmado": True,
                "deleted": False,
                "deleted_at": None,
            },
        )
        SecurityEvent.objects.create(
            usuario=user,
            evento="2fa_habilitado",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": _("2FA habilitado.")})

    @action(detail=False, methods=["post"], url_path="disable-2fa")
    def disable_2fa(self, request):
        user = request.user
        code = request.data.get("code")
        if not code:
            return Response({"detail": _("Código obrigatório.")}, status=400)
        if not user.two_factor_secret or not pyotp.TOTP(user.two_factor_secret).verify(code):
            return Response({"detail": _("Código inválido.")}, status=400)
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.save(update_fields=["two_factor_enabled", "two_factor_secret"])
        TOTPDevice.objects.filter(usuario=user).delete()
        SecurityEvent.objects.create(
            usuario=user,
            evento="2fa_desabilitado",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": _("2FA desabilitado.")})

    @action(detail=False, methods=["delete"], url_path="me")
    def delete_me(self, request):
        user = request.user
        user.delete()
        user.is_active = False
        user.exclusao_confirmada = True
        user.save(update_fields=["is_active", "exclusao_confirmada"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="conta_excluida",
            ip=request.META.get("REMOTE_ADDR"),
        )
        token = AccountToken.objects.create(
            usuario=user,
            tipo=AccountToken.Tipo.CANCEL_DELETE,
            expires_at=timezone.now() + timezone.timedelta(days=30),
            ip_gerado=request.META.get("REMOTE_ADDR"),
        )
        send_cancel_delete_email.delay(token.id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="me/cancel-delete")
    def cancel_delete(self, request):
        code = request.data.get("token")
        if not code:
            return Response({"detail": _("Token ausente.")}, status=400)
        try:
            token = AccountToken.objects.select_related("usuario").get(
                codigo=code,
                tipo=AccountToken.Tipo.CANCEL_DELETE,
            )
        except AccountToken.DoesNotExist:
            return Response({"detail": _("Token inválido ou expirado.")}, status=400)
        if token.expires_at < timezone.now() or token.used_at:
            return Response({"detail": _("Token inválido ou expirado.")}, status=400)

        user = token.usuario
        user.deleted = False
        user.deleted_at = None
        user.is_active = True
        user.exclusao_confirmada = False
        user.save(update_fields=["deleted", "deleted_at", "is_active", "exclusao_confirmada"])
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        ip = request.META.get("REMOTE_ADDR", "")
        SecurityEvent.objects.create(
            usuario=user,
            evento="cancelou_exclusao",
            ip=ip,
        )
        log_audit(
            user,
            "account_delete_canceled",
            object_type="User",
            object_id=str(user.id),
            ip_hash=hash_ip(ip),
            status=AuditLog.Status.SUCCESS,
        )
        return Response({"detail": _("Processo cancelado.")})
