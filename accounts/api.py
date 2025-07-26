from __future__ import annotations

import pyotp
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AccountToken, SecurityEvent
from .serializers import UserSerializer
from .tasks import send_confirmation_email, send_password_reset_email

User = get_user_model()


class AccountViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in {"delete_me", "cancel_delete", "enable_2fa", "disable_2fa", "resend_confirmation"}:
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
        token.usuario.save(update_fields=["is_active"])
        SecurityEvent.objects.create(
            usuario=token.usuario,
            evento="email_confirmado",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": _("Email confirmado.")})

    @action(detail=False, methods=["post"], url_path="resend-confirmation")
    def resend_confirmation(self, request):
        user = request.user
        if user.is_active:
            return Response({"detail": _("Conta já ativada.")}, status=400)
        token = AccountToken.objects.create(
            usuario=user,
            tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
            expires_at=timezone.now() + timezone.timedelta(hours=24),
            ip_gerado=request.META.get("REMOTE_ADDR"),
        )
        send_confirmation_email.delay(token.id)
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
        user.set_password(new_password)
        user.save(update_fields=["password"])
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
        secret = pyotp.random_base32()
        user.two_factor_secret = secret
        user.two_factor_enabled = True
        user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="2fa_habilitado",
            ip=request.META.get("REMOTE_ADDR"),
        )
        otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Hubx")
        return Response({"otpauth_url": otp_uri})

    @action(detail=False, methods=["post"], url_path="disable-2fa")
    def disable_2fa(self, request):
        user = request.user
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.save(update_fields=["two_factor_enabled", "two_factor_secret"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="2fa_desabilitado",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": _("2FA desabilitado.")})

    @action(detail=False, methods=["delete"], url_path="me")
    def delete_me(self, request):
        user = request.user
        user.deleted_at = timezone.now()
        user.exclusao_confirmada = True
        user.save(update_fields=["deleted_at", "exclusao_confirmada"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="conta_excluida",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="me/cancel-delete")
    def cancel_delete(self, request):
        user = request.user
        user.deleted_at = None
        user.exclusao_confirmada = False
        user.save(update_fields=["deleted_at", "exclusao_confirmada"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="cancelou_exclusao",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return Response({"detail": _("Processo cancelado.")})
