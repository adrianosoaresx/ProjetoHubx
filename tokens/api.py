from __future__ import annotations

import hashlib
import time

import sentry_sdk
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType
from audit.models import AuditLog
from audit.services import hash_ip, log_audit

from .metrics import (
    tokens_api_latency_seconds,
    tokens_invites_created_total,
    tokens_invites_revoked_total,
    tokens_invites_used_total,
    tokens_rate_limited_total,
    tokens_validation_fail_total,
    tokens_validation_latency_seconds,
)
from .models import TokenAcesso, TokenUsoLog
from .perms import can_issue_invite
from .ratelimit import check_rate_limit
from .serializers import TokenAcessoSerializer, TokenUsoLogSerializer
from .services import create_invite_token, find_token_by_code


class TokenViewSet(viewsets.GenericViewSet):
    queryset = TokenAcesso.objects.select_related(
        "gerado_por",
        "usuario",
        "revogado_por",
        "organizacao",
    ).prefetch_related("nucleos")
    serializer_class = TokenAcessoSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        start_time = time.perf_counter()
        ip = request.META.get("REMOTE_ADDR", "")
        target_role = request.data.get("tipo_destino")
        if not can_issue_invite(request.user, target_role):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("module", "tokens")
                scope.set_context("invite", {"target_role": target_role, "user_id": request.user.id})
                sentry_sdk.capture_message("token_invite_denied", level="warning")
            log_audit(
                request.user,
                "token_invite_denied",
                object_type="TokenAcesso",
                ip_hash=hash_ip(ip),
                status=AuditLog.Status.FAILURE,
                metadata={"target_role": target_role},
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        start_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = start_day + timezone.timedelta(days=1)
        if (
            TokenAcesso.objects.filter(
                gerado_por=request.user,
                created_at__gte=start_day,
                created_at__lt=end_day,
            ).count()
            >= 5
        ):
            tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
            return Response(
                {"detail": _("Limite diário atingido.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            token, codigo = create_invite_token(
                gerado_por=request.user,
                tipo_destino=serializer.validated_data["tipo_destino"],
                data_expiracao=serializer.validated_data.get("data_expiracao"),
                organizacao=serializer.validated_data.get("organizacao"),
            )
            token.ip_gerado = ip
            token.save(update_fields=["ip_gerado"])
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.GERACAO,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("module", "tokens")
            scope.set_context("invite", {"token_id": str(token.id), "user_id": request.user.id})
            sentry_sdk.capture_message("token_invite_created")
        log_audit(
            request.user,
            "token_invite_created",
            object_type="TokenAcesso",
            object_id=str(token.id),
            ip_hash=hash_ip(ip),
            metadata={"target_role": target_role},
        )
        token.codigo = codigo
        out = self.get_serializer(token)
        tokens_invites_created_total.inc()
        tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="validate", url_name="validate")
    def validate_token(self, request):
        start = time.perf_counter()
        codigo = request.query_params.get("codigo")
        if not codigo:
            tokens_validation_fail_total.inc()
            return Response({"detail": _("Código ausente.")}, status=400)
        ip = request.META.get("REMOTE_ADDR", "")
        code_hash = hashlib.sha256(codigo.encode()).hexdigest()
        rl1 = check_rate_limit(f"code:{code_hash}:{ip}")
        rl2 = check_rate_limit(f"user:{request.user.id}:{ip}") if request.user.is_authenticated else None
        if not rl1.allowed or (rl2 and not rl2.allowed):
            tokens_rate_limited_total.inc()
            retry = rl1.retry_after if rl1.retry_after else (rl2.retry_after if rl2 else 0)
            resp = Response({"detail": "rate limit exceeded"}, status=429)
            if retry:
                resp["Retry-After"] = str(retry)
            tokens_validation_latency_seconds.observe(time.perf_counter() - start)
            return resp
        try:
            token = find_token_by_code(codigo)
        except TokenAcesso.DoesNotExist:
            tokens_validation_fail_total.inc()
            tokens_validation_latency_seconds.observe(time.perf_counter() - start)
            return Response({"detail": _("Token inválido.")}, status=404)

        if token.estado == TokenAcesso.Estado.REVOGADO:
            tokens_validation_fail_total.inc()
            tokens_validation_latency_seconds.observe(time.perf_counter() - start)
            return Response({"detail": _("Token revogado.")}, status=status.HTTP_409_CONFLICT)
        if token.estado != TokenAcesso.Estado.NOVO:
            tokens_validation_fail_total.inc()
            tokens_validation_latency_seconds.observe(time.perf_counter() - start)
            return Response({"detail": _("Token inválido.")}, status=status.HTTP_409_CONFLICT)
        if token.data_expiracao and token.data_expiracao < timezone.now():
            token.estado = TokenAcesso.Estado.EXPIRADO
            token.save(update_fields=["estado"])
            tokens_validation_fail_total.inc()
            tokens_validation_latency_seconds.observe(time.perf_counter() - start)
            return Response({"detail": _("Token expirado.")}, status=status.HTTP_409_CONFLICT)

        token.ip_utilizado = ip
        token.save(update_fields=["ip_utilizado"])
        TokenUsoLog.objects.create(
            token=token,
            usuario=request.user if request.user.is_authenticated else None,
            acao=TokenUsoLog.Acao.VALIDACAO,
            ip=ip,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        token.codigo = codigo
        out = self.get_serializer(token)
        tokens_validation_latency_seconds.observe(time.perf_counter() - start)
        return Response(out.data)

    @action(detail=True, methods=["post"])
    def use(self, request, pk: str | None = None):
        start_time = time.perf_counter()
        token = self.get_object()
        ip = request.META.get("REMOTE_ADDR", "")
        rl1 = check_rate_limit(f"token:{token.id}:{ip}")
        rl2 = check_rate_limit(f"user:{request.user.id}:{ip}")
        if not rl1.allowed or not rl2.allowed:
            tokens_rate_limited_total.inc()
            retry = max(rl1.retry_after, rl2.retry_after)
            resp = Response({"detail": "rate limit exceeded"}, status=429)
            if retry:
                resp["Retry-After"] = str(retry)
            tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
            return resp
        if token.estado in {
            TokenAcesso.Estado.USADO,
            TokenAcesso.Estado.EXPIRADO,
            TokenAcesso.Estado.REVOGADO,
        }:
            tokens_validation_fail_total.inc()
            tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
            return Response({"detail": _("Token inválido.")}, status=status.HTTP_409_CONFLICT)
        with transaction.atomic():
            token.estado = TokenAcesso.Estado.USADO
            token.usuario = request.user
            token.ip_utilizado = ip
            token.save(update_fields=["estado", "usuario", "ip_utilizado"])
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.USO,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        tokens_invites_used_total.inc()
        tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
        out = self.get_serializer(token)
        return Response(out.data)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"(?P<codigo>[^/]+)/revogar",
        url_name="revogar",
    )
    def revogar(self, request, codigo: str | None = None):
        start_time = time.perf_counter()
        if request.user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
            return Response(status=403)
        try:
            token = find_token_by_code(codigo)
        except TokenAcesso.DoesNotExist:
            tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
            return Response(status=404)
        if token.estado == TokenAcesso.Estado.REVOGADO:
            tokens_validation_fail_total.inc()
            tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
            return Response({"detail": _("Token já revogado.")}, status=status.HTTP_409_CONFLICT)
        now = timezone.now()
        ip = request.META.get("REMOTE_ADDR", "")
        with transaction.atomic():
            token.estado = TokenAcesso.Estado.REVOGADO
            token.revogado_em = now
            token.revogado_por = request.user
            token.save(update_fields=["estado", "revogado_em", "revogado_por"])
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.REVOGACAO,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        tokens_invites_revoked_total.inc()
        tokens_api_latency_seconds.observe(time.perf_counter() - start_time)
        token.codigo = codigo
        out = self.get_serializer(token)
        return Response(out.data)

    @action(detail=True, methods=["get"], url_path="logs")
    def listar_logs(self, request, pk: str | None = None):
        if request.user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            return Response(status=403)
        token = self.get_object()
        logs = token.logs.select_related("usuario")
        serializer = TokenUsoLogSerializer(logs, many=True)
        return Response(serializer.data)
