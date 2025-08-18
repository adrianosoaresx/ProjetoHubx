from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType
from accounts.serializers import UserSerializer
from agenda.models import Evento
from agenda.serializers import EventoSerializer
from empresas.models import Empresa
from empresas.serializers import EmpresaSerializer
from feed.api import PostSerializer
from feed.models import Post
from nucleos.models import Nucleo
from nucleos.serializers import NucleoSerializer

from core.permissions import IsOrgAdminOrSuperuser, IsRoot

from .models import Organizacao, OrganizacaoAtividadeLog
from .serializers import (
    OrganizacaoAtividadeLogSerializer,
    OrganizacaoChangeLogSerializer,
    OrganizacaoSerializer,
)
from .tasks import organizacao_alterada


class OrganizacaoViewSet(viewsets.ModelViewSet):
    queryset = Organizacao.objects.all()
    serializer_class = OrganizacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if (
            user.is_superuser
            or user.get_tipo_usuario == UserType.ROOT.value
            or getattr(user, "user_type", None) == UserType.ROOT.value
        ):
            pass
        elif user.get_tipo_usuario == UserType.ADMIN.value or getattr(user, "user_type", None) == UserType.ADMIN.value:
            org_id = getattr(user, "organizacao_id", None)
            if org_id is None:
                raise PermissionDenied
            qs = qs.filter(pk=org_id)
        else:
            raise PermissionDenied
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(slug__icontains=search))
        inativa = self.request.query_params.get("inativa")
        if inativa is not None:
            qs = qs.filter(inativa=inativa.lower() == "true")
        else:
            qs = qs.filter(inativa=False)
        ordering = self.request.query_params.get("ordering")
        allowed = {"nome", "tipo", "cidade", "estado", "created_at"}
        if ordering and ordering.lstrip("-") in allowed:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("nome")
        return qs

    def get_permissions(self):
        if self.action in {
            "create",
            "destroy",
            "partial_update",
            "update",
            "inativar",
            "reativar",
        }:
            self.permission_classes = [IsAuthenticated, IsRoot]
        elif self.action in {"history", "list", "retrieve"}:
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
        organizacao = Organizacao.objects.get(pk=pk)
        self.check_object_permissions(request, organizacao)
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
            for log in (
                OrganizacaoChangeLog.all_objects.filter(organizacao=organizacao)
                .order_by("-created_at")
            ):
                writer.writerow(
                    [
                        "change",
                        log.campo_alterado,
                        log.valor_antigo,
                        log.valor_novo,
                        getattr(log.alterado_por, "email", ""),
                        log.created_at.isoformat(),
                    ]
                )
            for log in (
                OrganizacaoAtividadeLog.all_objects.filter(organizacao=organizacao)
                .order_by("-created_at")
            ):
                writer.writerow(
                    [
                        "activity",
                        log.acao,
                        "",
                        "",
                        getattr(log.usuario, "email", ""),
                        log.created_at.isoformat(),
                    ]
                )
            return response
        change_logs = (
            OrganizacaoChangeLog.all_objects.filter(organizacao=organizacao)
            .order_by("-created_at")[:10]
        )
        atividade_logs = (
            OrganizacaoAtividadeLog.all_objects.filter(organizacao=organizacao)
            .order_by("-created_at")[:10]
        )
        change_ser = OrganizacaoChangeLogSerializer(change_logs, many=True)
        atividade_ser = OrganizacaoAtividadeLogSerializer(atividade_logs, many=True)
        return Response({"changes": change_ser.data, "activities": atividade_ser.data})


class OrganizacaoRelatedViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_organizacao(self):
        org = get_object_or_404(Organizacao, pk=self.kwargs["organizacao_pk"])
        perm = IsOrgAdminOrSuperuser()
        if not perm.has_object_permission(self.request, self, org):
            raise PermissionDenied()
        return org


class OrganizacaoUserViewSet(OrganizacaoRelatedViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return org.users.all()

    @action(detail=False, methods=["get"], url_path="associados")
    def associados(self, request, organizacao_pk: str | None = None):
        qs = self.get_queryset().filter(user_type=UserType.ASSOCIADO.value)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class OrganizacaoNucleoViewSet(OrganizacaoRelatedViewSet):
    serializer_class = NucleoSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Nucleo.objects.filter(organizacao=org, deleted=False)


class OrganizacaoEventoViewSet(OrganizacaoRelatedViewSet):
    serializer_class = EventoSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Evento.objects.filter(organizacao=org, deleted=False)


class OrganizacaoEmpresaViewSet(OrganizacaoRelatedViewSet):
    serializer_class = EmpresaSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Empresa.objects.filter(organizacao=org, deleted=False)


class OrganizacaoPostViewSet(OrganizacaoRelatedViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Post.objects.filter(organizacao=org, deleted=False)
