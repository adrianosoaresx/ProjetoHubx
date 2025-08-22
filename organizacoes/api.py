from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sentry_sdk import capture_exception

from accounts.models import UserType
from accounts.serializers import UserSerializer
from agenda.models import Evento
from agenda.serializers import EventoSerializer
from core.cache import get_cache_version
from core.permissions import IsOrgAdminOrSuperuser, IsRoot
from empresas.models import Empresa
from empresas.serializers import EmpresaSerializer
from feed.api import PostSerializer
from feed.models import FeedPluginConfig, Post
from financeiro.models import CentroCusto
from financeiro.serializers import CentroCustoSerializer
from nucleos.models import Nucleo
from nucleos.serializers import NucleoSerializer

from .metrics import detail_latency_seconds, list_latency_seconds
from .models import (
    Organizacao,
    OrganizacaoAtividadeLog,
    OrganizacaoChangeLog,
    OrganizacaoRecurso,
)
from .serializers import (
    FeedPluginConfigSerializer,
    OrganizacaoAtividadeLogSerializer,
    OrganizacaoChangeLogSerializer,
    OrganizacaoRecursoSerializer,
    OrganizacaoSerializer,
)
from .tasks import organizacao_alterada


class OrganizacaoViewSet(viewsets.ModelViewSet):
    queryset = Organizacao.objects.all()
    serializer_class = OrganizacaoSerializer
    permission_classes = [IsAuthenticated]
    cache_timeout = 60

    def get_queryset(self):
        qs = super().get_queryset().select_related("created_by").prefetch_related("users")
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
                e = PermissionDenied()
                capture_exception(e)
                raise e
            qs = qs.filter(pk=org_id)
        else:
            e = PermissionDenied()
            capture_exception(e)
            raise e

        params = self.request.query_params
        search = params.get("search")
        tipo = params.get("tipo")
        cidade = params.get("cidade")
        estado = params.get("estado")
        inativa = params.get("inativa")
        if inativa is not None:
            qs = qs.filter(inativa=inativa.lower() == "true")

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(slug__icontains=search))
        inativa = self.request.query_params.get("inativa")
        if inativa not in (None, ""):
            value = inativa.lower()
            truthy = {"1", "true", "t", "yes"}
            falsy = {"0", "false", "f", "no"}
            if value in truthy:
                qs = qs.filter(inativa=True)
            elif value in falsy:
                qs = qs.filter(inativa=False)
            else:
                qs = qs.filter(inativa=False)

        else:
            qs = qs.filter(inativa=False)
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(slug__icontains=search))
        if tipo:
            qs = qs.filter(tipo=tipo)
        if cidade:
            qs = qs.filter(cidade=cidade)
        if estado:
            qs = qs.filter(estado=estado)
        ordering = params.get("ordering")
        allowed = {"nome", "tipo", "cidade", "estado", "created_at"}
        if ordering and ordering.lstrip("-") in allowed:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("nome")
        return qs

    def _cache_key(self, request) -> str:
        params = request.query_params
        version = get_cache_version("organizacoes_list")
        keys = [
            str(getattr(request.user, "pk", "")),
            params.get("search", ""),
            params.get("tipo", ""),
            params.get("cidade", ""),
            params.get("estado", ""),
            params.get("inativa", ""),
            params.get("ordering", ""),
            params.get("page", ""),
            params.get("page_size", ""),
        ]
        return f"organizacoes_list_v{version}_" + "_".join(keys)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        with list_latency_seconds.time():
            key = self._cache_key(request)
            cached = cache.get(key)
            if cached is not None:
                response = Response(cached)
                response["X-Cache"] = "HIT"
                return response
            response = super().list(request, *args, **kwargs)
            cache.set(key, response.data, self.cache_timeout)
            response["X-Cache"] = "MISS"
            return response

    def retrieve(self, request, *args, **kwargs):  # type: ignore[override]
        with detail_latency_seconds.time():
            return super().retrieve(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in {
            "create",
            "destroy",
            "partial_update",
            "update",
            "inativar",
            "reativar",
            "history",
        }:
            self.permission_classes = [IsAuthenticated, IsRoot]
        elif self.action in {"list", "retrieve"}:
            self.permission_classes = [IsAuthenticated, IsOrgAdminOrSuperuser]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

    def update(self, request, *args, **kwargs):  # type: ignore[override]
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

    def partial_update(self, request, *args, **kwargs):  # type: ignore[override]
        try:
            return super().partial_update(request, *args, **kwargs)
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

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
        try:
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
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsRoot])
    def reativar(self, request, pk: str | None = None):
        try:
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
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk: str | None = None):
        try:
            organizacao = self.get_object()
            if request.query_params.get("export") == "csv":
                import csv

                from django.http import HttpResponse

                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = f'attachment; filename="organizacao_{organizacao.pk}_logs.csv"'
                writer = csv.writer(response)
                writer.writerow(["tipo", "campo/acao", "valor_antigo", "valor_novo", "usuario", "data"])
                for log in OrganizacaoChangeLog.all_objects.filter(organizacao=organizacao).order_by("-created_at"):
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
                for log in OrganizacaoAtividadeLog.all_objects.filter(organizacao=organizacao).order_by("-created_at"):
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
            change_logs = OrganizacaoChangeLog.all_objects.filter(organizacao=organizacao).order_by("-created_at")[:10]
            atividade_logs = OrganizacaoAtividadeLog.all_objects.filter(organizacao=organizacao).order_by(
                "-created_at"
            )[:10]
            change_ser = OrganizacaoChangeLogSerializer(change_logs, many=True)
            atividade_ser = OrganizacaoAtividadeLogSerializer(atividade_logs, many=True)
            return Response({"changes": change_ser.data, "activities": atividade_ser.data})
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise


class OrganizacaoRelatedViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_organizacao(self):
        org = get_object_or_404(Organizacao, pk=self.kwargs["organizacao_pk"])
        perm = IsOrgAdminOrSuperuser()
        if not perm.has_object_permission(self.request, self, org):
            e = PermissionDenied()
            capture_exception(e)
            raise e
        return org


class OrganizacaoRelatedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_organizacao(self):
        org = get_object_or_404(Organizacao, pk=self.kwargs["organizacao_pk"])
        perm = IsOrgAdminOrSuperuser()
        if not perm.has_object_permission(self.request, self, org):
            e = PermissionDenied()
            capture_exception(e)
            raise e
        return org


class OrganizacaoUserViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return org.users.all()

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        qs = get_user_model().objects.filter(organizacao__isnull=True)
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(username__icontains=search)
            )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        user_id = request.data.get("user_id")
        user = get_object_or_404(get_user_model(), pk=user_id)
        user.organizacao = org
        user.save(update_fields=["organizacao"])
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, organizacao_pk=None):  # type: ignore[override]
        org = self.get_organizacao()
        user = get_object_or_404(get_user_model(), pk=pk, organizacao=org)
        user.organizacao = None
        user.save(update_fields=["organizacao"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="associados")
    def associados(self, request, organizacao_pk: str | None = None):
        qs = self.get_queryset().filter(user_type=UserType.ASSOCIADO.value)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class OrganizacaoNucleoViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = NucleoSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Nucleo.objects.filter(organizacao=org, deleted=False)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        qs = Nucleo.objects.filter(deleted=False).exclude(organizacao=org)
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(nome__icontains=search)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        nucleo_id = request.data.get("nucleo_id")
        nucleo = get_object_or_404(Nucleo, pk=nucleo_id)
        nucleo.organizacao = org
        nucleo.save(update_fields=["organizacao"])
        serializer = self.get_serializer(nucleo)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, organizacao_pk=None):  # type: ignore[override]
        org = self.get_organizacao()
        nucleo = get_object_or_404(Nucleo, pk=pk, organizacao=org)
        nucleo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizacaoEventoViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = EventoSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Evento.objects.filter(organizacao=org, deleted=False)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        qs = Evento.objects.filter(deleted=False).exclude(organizacao=org)
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(titulo__icontains=search)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        evento_id = request.data.get("evento_id")
        evento = get_object_or_404(Evento, pk=evento_id)
        evento.organizacao = org
        evento.save(update_fields=["organizacao"])
        serializer = self.get_serializer(evento)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, organizacao_pk=None):  # type: ignore[override]
        org = self.get_organizacao()
        evento = get_object_or_404(Evento, pk=pk, organizacao=org)
        evento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizacaoEmpresaViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = EmpresaSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Empresa.objects.filter(organizacao=org, deleted=False)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        qs = Empresa.objects.filter(deleted=False).exclude(organizacao=org)
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(nome__icontains=search)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        empresa_id = request.data.get("empresa_id")
        empresa = get_object_or_404(Empresa, pk=empresa_id)
        empresa.organizacao = org
        empresa.save(update_fields=["organizacao"])
        serializer = self.get_serializer(empresa)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, organizacao_pk=None):  # type: ignore[override]
        org = self.get_organizacao()
        empresa = get_object_or_404(Empresa, pk=pk, organizacao=org)
        empresa.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizacaoPostViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return Post.objects.filter(organizacao=org, deleted=False)

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        qs = Post.objects.filter(deleted=False).exclude(organizacao=org)
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(conteudo__icontains=search)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # type: ignore[override]
        org = self.get_organizacao()
        post_id = request.data.get("post_id")
        post = get_object_or_404(Post, pk=post_id)
        post.organizacao = org
        post.save(update_fields=["organizacao"])
        serializer = self.get_serializer(post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, organizacao_pk=None):  # type: ignore[override]
        org = self.get_organizacao()
        post = get_object_or_404(Post, pk=pk, organizacao=org)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizacaoCentroCustoViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = CentroCustoSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return CentroCusto.objects.filter(organizacao=org, deleted=False)

    def perform_create(self, serializer):
        serializer.save(organizacao=self.get_organizacao())


class OrganizacaoPluginViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = FeedPluginConfigSerializer

    def get_queryset(self):
        org = self.get_organizacao()
        return FeedPluginConfig.objects.filter(organizacao=org)

    def perform_create(self, serializer):
        serializer.save(organizacao=self.get_organizacao())


class OrganizacaoRecursoViewSet(OrganizacaoRelatedModelViewSet):
    serializer_class = OrganizacaoRecursoSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        org = self.get_organizacao()
        return OrganizacaoRecurso.objects.filter(organizacao=org, deleted=False)

    def perform_create(self, serializer):
        serializer.save(organizacao=self.get_organizacao())
