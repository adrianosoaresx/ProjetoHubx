from __future__ import annotations

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsRoot

from .models import Organizacao, OrganizacaoLog
from .serializers import OrganizacaoLogSerializer, OrganizacaoSerializer
from .tasks import organizacao_alterada


class OrganizacaoViewSet(viewsets.ModelViewSet):
    queryset = Organizacao.objects.filter(deleted=False)
    serializer_class = OrganizacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset().order_by("nome")
        inativa = self.request.query_params.get("inativa")
        if inativa is not None:
            qs = qs.filter(inativa=inativa.lower() == "true")
        return qs

    def get_permissions(self):
        if self.action in {"create", "destroy", "partial_update", "update", "inativar", "reativar", "logs"}:
            self.permission_classes = [IsAuthenticated, IsRoot]
        return super().get_permissions()

    def perform_destroy(self, instance: Organizacao) -> None:
        instance.delete()
        OrganizacaoLog.objects.create(
            organizacao=instance,
            usuario=self.request.user,
            acao="deleted",
            dados_antigos={},
            dados_novos={"deleted": True, "deleted_at": instance.deleted_at.isoformat()},
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="deleted")

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsRoot])
    def inativar(self, request, pk: str | None = None):
        organizacao = self.get_object()
        organizacao.inativa = True
        organizacao.inativada_em = timezone.now()
        organizacao.save(update_fields=["inativa", "inativada_em"])
        OrganizacaoLog.objects.create(
            organizacao=organizacao,
            usuario=request.user,
            acao="inactivated",
            dados_antigos={},
            dados_novos={"inativa": True, "inativada_em": organizacao.inativada_em.isoformat()},
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=organizacao, acao="inactivated")
        serializer = self.get_serializer(organizacao)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsRoot])
    def reativar(self, request, pk: str | None = None):
        organizacao = self.get_object()
        organizacao.inativa = False
        organizacao.inativada_em = None
        organizacao.save(update_fields=["inativa", "inativada_em"])
        OrganizacaoLog.objects.create(
            organizacao=organizacao,
            usuario=request.user,
            acao="reactivated",
            dados_antigos={},
            dados_novos={"inativa": False, "inativada_em": None},
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=organizacao, acao="reactivated")
        serializer = self.get_serializer(organizacao)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsRoot])
    def logs(self, request, pk: str | None = None):
        organizacao = self.get_object()
        logs = organizacao.logs.all()
        serializer = OrganizacaoLogSerializer(logs, many=True)
        return Response(serializer.data)
