from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .models import TokenAcesso, TokenUsoLog
from .serializers import TokenAcessoSerializer, TokenUsoLogSerializer


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
        ip = request.META.get("REMOTE_ADDR")
        agent = request.META.get("HTTP_USER_AGENT", "")
        start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timezone.timedelta(days=1)
        if (
            TokenAcesso.objects.filter(
                gerado_por=request.user,
                created_at__gte=start,
                created_at__lt=end,
            ).count()
            >= 5
        ):
            return Response({"detail": _("Limite diário atingido.")}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            token: TokenAcesso = serializer.save(gerado_por=request.user, ip_gerado=ip)
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.GERACAO,
                ip=ip,
                user_agent=agent,
            )
        out = self.get_serializer(token)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="validate", url_name="validate")
    def validate_token(self, request):
        codigo = request.query_params.get("codigo")
        if not codigo:
            return Response({"detail": _("Código ausente.")}, status=400)
        token = get_object_or_404(TokenAcesso, codigo=codigo)
        if token.estado == TokenAcesso.Estado.REVOGADO:
            return Response({"detail": _("Token revogado.")}, status=status.HTTP_409_CONFLICT)
        if token.estado != TokenAcesso.Estado.NOVO:
            return Response({"detail": _("Token inválido.")}, status=status.HTTP_409_CONFLICT)
        if token.data_expiracao and token.data_expiracao < timezone.now():
            token.estado = TokenAcesso.Estado.EXPIRADO
            token.save(update_fields=["estado"])
            return Response({"detail": _("Token expirado.")}, status=status.HTTP_409_CONFLICT)
        ip = request.META.get("REMOTE_ADDR")
        agent = request.META.get("HTTP_USER_AGENT", "")
        token.ip_utilizado = ip
        token.save(update_fields=["ip_utilizado"])
        TokenUsoLog.objects.create(
            token=token,
            usuario=request.user if request.user.is_authenticated else None,
            acao=TokenUsoLog.Acao.VALIDACAO,
            ip=ip,
            user_agent=agent,
        )
        out = self.get_serializer(token)
        return Response(out.data)

    @action(detail=True, methods=["post"])
    def use(self, request, pk: str | None = None):
        token = self.get_object()
        if token.estado in {
            TokenAcesso.Estado.USADO,
            TokenAcesso.Estado.EXPIRADO,
            TokenAcesso.Estado.REVOGADO,
        }:
            return Response({"detail": _("Token inválido.")}, status=status.HTTP_409_CONFLICT)
        ip = request.META.get("REMOTE_ADDR")
        agent = request.META.get("HTTP_USER_AGENT", "")
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
                user_agent=agent,
            )
        out = self.get_serializer(token)
        return Response(out.data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk: str | None = None):
        if request.user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            return Response(status=403)
        token = self.get_object()
        if token.estado == TokenAcesso.Estado.REVOGADO:
            return Response({"detail": _("Token já revogado.")}, status=status.HTTP_409_CONFLICT)
        now = timezone.now()
        ip = request.META.get("REMOTE_ADDR")
        agent = request.META.get("HTTP_USER_AGENT", "")
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
                user_agent=agent,
            )
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
