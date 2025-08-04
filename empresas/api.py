from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .models import AvaliacaoEmpresa, Empresa
from .serializers import (
    AvaliacaoEmpresaSerializer,
    EmpresaChangeLogSerializer,
    EmpresaSerializer,
)
from .tasks import nova_avaliacao


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = (
        Empresa.objects.filter(deleted=False)
        .select_related("usuario", "organizacao")
        .prefetch_related("tags")
    )
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        nome = self.request.query_params.get("nome")
        tag_ids = self.request.query_params.getlist("tag")
        termo = self.request.query_params.get("q")
        if nome:
            qs = qs.filter(nome__icontains=nome)
        if termo:
            qs = qs.filter(palavras_chave__icontains=termo)
        if tag_ids:
            qs = qs.filter(tags__id__in=tag_ids).distinct()
        return qs.order_by("nome")

    def perform_destroy(self, instance: Empresa) -> None:
        instance.deleted = True
        instance.save(update_fields=["deleted"])

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        empresa = self.get_object()
        if not (
            request.user == empresa.usuario
            or request.user.get_tipo_usuario in {UserType.ADMIN.value, UserType.ROOT.value}
        ):
            return Response(status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        empresa = self.get_object()
        if not (
            request.user == empresa.usuario
            or request.user.get_tipo_usuario in {UserType.ADMIN.value, UserType.ROOT.value}
        ):
            return Response(status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def avaliacoes(self, request, pk: str | None = None):
        empresa = self.get_object()
        if request.user.organizacao != empresa.organizacao:
            return Response({"detail": "Usuário não pertence à organização."}, status=403)
        if AvaliacaoEmpresa.objects.filter(
            empresa=empresa, usuario=request.user, deleted=False
        ).exists():
            return Response({"detail": "Avaliação já registrada."}, status=400)
        serializer = AvaliacaoEmpresaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        avaliacao = AvaliacaoEmpresa.objects.create(
            empresa=empresa,
            usuario=request.user,
            nota=serializer.validated_data["nota"],
            comentario=serializer.validated_data.get("comentario", ""),
        )
        nova_avaliacao.send(sender=self.__class__, avaliacao=avaliacao)
        out = AvaliacaoEmpresaSerializer(avaliacao)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @avaliacoes.mapping.get
    def listar_avaliacoes(self, request, pk: str | None = None):
        empresa = self.get_object()
        avals = empresa.avaliacoes.filter(deleted=False).select_related("usuario")
        serializer = AvaliacaoEmpresaSerializer(avals, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def historico(self, request, pk: str | None = None):
        if not request.user.is_staff:
            return Response(status=403)
        empresa = self.get_object()
        logs = empresa.logs.filter(deleted=False).select_related("usuario")
        serializer = EmpresaChangeLogSerializer(logs, many=True)
        return Response(serializer.data)
