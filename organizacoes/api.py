from __future__ import annotations

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsRoot, IsOrgAdminOrSuperuser

from .models import Organizacao, OrganizacaoAtividadeLog, OrganizacaoChangeLog
from .serializers import (
    OrganizacaoAtividadeLogSerializer,
    OrganizacaoChangeLogSerializer,
    OrganizacaoSerializer,
)
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
        if self.action in {"create", "destroy", "partial_update", "update", "inativar", "reativar"}:
            self.permission_classes = [IsAuthenticated, IsRoot]
        elif self.action in {"history"}:
            self.permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
        return super().get_permissions()

    def perform_destroy(self, instance: Organizacao) -> None:
        instance.delete()
        OrganizacaoAtividadeLog.objects.create(
            organizacao=instance,
            usuario=self.request.user,
            acao="deleted",
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="deleted")

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsRoot])
    def inativar(self, request, pk: str | None = None):
        organizacao = self.get_object()
        organizacao.inativa = True
        organizacao.inativada_em = timezone.now()
        organizacao.save(update_fields=["inativa", "inativada_em"])
        OrganizacaoAtividadeLog.objects.create(
            organizacao=organizacao,
            usuario=request.user,
            acao="inactivated",
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
        OrganizacaoAtividadeLog.objects.create(
            organizacao=organizacao,
            usuario=request.user,
            acao="reactivated",
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=organizacao, acao="reactivated")
        serializer = self.get_serializer(organizacao)
        return Response(serializer.data)
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk: str | None = None):
        organizacao = self.get_object()
        if request.query_params.get("export") == "csv":
            import csv
            from django.http import HttpResponse

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="organizacao_{organizacao.pk}_logs.csv"'
            writer = csv.writer(response)
            writer.writerow(["tipo", "campo/acao", "valor_antigo", "valor_novo", "usuario", "data"])
            for log in organizacao.change_logs.all().order_by("-alterado_em"):
                writer.writerow(
                    [
                        "change",
                        log.campo_alterado,
                        log.valor_antigo,
                        log.valor_novo,
                        getattr(log.alterado_por, "email", ""),
                        log.alterado_em.isoformat(),
                    ]
                )
            for log in organizacao.atividade_logs.all().order_by("-data"):
                writer.writerow(
                    [
                        "activity",
                        log.acao,
                        "",
                        "",
                        getattr(log.usuario, "email", ""),
                        log.data.isoformat(),
                    ]
                )
            return response
        change_logs = organizacao.change_logs.all().order_by("-alterado_em")[:10]
        atividade_logs = organizacao.atividade_logs.all().order_by("-data")[:10]
        change_ser = OrganizacaoChangeLogSerializer(change_logs, many=True)
        atividade_ser = OrganizacaoAtividadeLogSerializer(atividade_logs, many=True)
        return Response({"changes": change_ser.data, "activities": atividade_ser.data})
