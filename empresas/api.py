from __future__ import annotations
from rest_framework import filters, status, viewsets
from django.shortcuts import get_object_or_404
from django.http import QueryDict
from rest_framework import status, viewsets

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserType

from .metrics import (
    empresas_favoritos_total,
    empresas_purgadas_total,
    empresas_restauradas_total,
)

from .models import AvaliacaoEmpresa, Empresa, EmpresaChangeLog, FavoritoEmpresa, Tag
from core.permissions import pode_crud_empresa
from .models import ContatoEmpresa, AvaliacaoEmpresa, Empresa, EmpresaChangeLog, FavoritoEmpresa
from .serializers import (
    AvaliacaoEmpresaSerializer,
    ContatoEmpresaSerializer,
    EmpresaChangeLogSerializer,
    EmpresaSerializer,
    TagSerializer,
)
from .tasks import nova_avaliacao
from .services import search_empresas, verificar_cnpj


class ContatoEmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = ContatoEmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContatoEmpresa.objects.filter(
            empresa_id=self.kwargs["empresa_pk"], deleted=False
        )

    def list(self, request, *args, **kwargs):
        empresa = get_object_or_404(Empresa, pk=self.kwargs["empresa_pk"])
        if not pode_crud_empresa(request.user, empresa):
            return Response(status=403)
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        empresa = get_object_or_404(Empresa, pk=self.kwargs["empresa_pk"])
        if not pode_crud_empresa(request.user, empresa):
            return Response(status=403)
        serializer = self.get_serializer(data=request.data, context={"empresa": empresa})
        serializer.is_valid(raise_exception=True)
        serializer.save(empresa=empresa)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        contato = get_object_or_404(
            ContatoEmpresa,
            pk=self.kwargs["pk"],
            empresa_id=self.kwargs["empresa_pk"],
            deleted=False,
        )
        if not pode_crud_empresa(request.user, contato.empresa):
            return Response(status=403)
        serializer = self.get_serializer(
            contato,
            data=request.data,
            partial=partial,
            context={"empresa": contato.empresa},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        contato = get_object_or_404(
            ContatoEmpresa,
            pk=self.kwargs["pk"],
            empresa_id=self.kwargs["empresa_pk"],
            deleted=False,
        )
        if not pode_crud_empresa(request.user, contato.empresa):
            return Response(status=403)
        contato.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("nome")
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["nome"]


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.select_related("usuario", "organizacao").prefetch_related("tags")
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset
        if getattr(self, "action", None) not in {"restaurar", "purgar"}:
            qs = qs.filter(deleted=False)
        nome = self.request.query_params.get("nome")
        tag_ids = self.request.query_params.getlist("tag")
        termo = self.request.query_params.get("q")
        palavras = self.request.query_params.get("palavras_chave")
        if nome:
            qs = qs.filter(nome__icontains=nome)
        if termo:
            qs = qs.filter(palavras_chave__icontains=termo)
        if palavras:
            qs = qs.filter(palavras_chave__icontains=palavras)
        if tag_ids:
            for tag_id in tag_ids:
                qs = qs.filter(tags__id=tag_id)
            qs = qs.distinct()
        user = self.request.user
        if user.is_superuser:
            pass
        elif user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type in {UserType.COORDENADOR, UserType.NUCLEADO}:
            qs = qs.filter(usuario=user)
        else:
            return Empresa.objects.none()
        return qs.order_by("nome")


    def perform_destroy(self, instance: Empresa) -> None:
        old_deleted = instance.deleted
        instance.deleted = True
        instance.save(update_fields=["deleted"])
        EmpresaChangeLog.objects.create(
            empresa=instance,
            usuario=self.request.user,
            campo_alterado="deleted",
            valor_antigo=str(old_deleted),
            valor_novo="True",
        )

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        empresa = self.get_object()
        if not (request.user == empresa.usuario or request.user.user_type in {UserType.ADMIN, UserType.ROOT}):
            return Response(status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        empresa = self.get_object()
        if not (request.user == empresa.usuario or request.user.user_type in {UserType.ADMIN, UserType.ROOT}):
            return Response(status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def validar_cnpj(self, request):
        cnpj = request.data.get("cnpj")
        if not cnpj:
            return Response({"detail": "cnpj é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        resultado = verificar_cnpj(cnpj)
        return Response(resultado)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def favoritos(self, request):
        empresas = self.get_queryset().filter(favoritos__usuario=request.user, favoritos__deleted=False)
        serializer = self.get_serializer(empresas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def favoritar(self, request, pk: str | None = None):
        empresa = self.get_object()
        if request.user.organizacao != empresa.organizacao:
            return Response(status=403)
        FavoritoEmpresa.objects.get_or_create(usuario=request.user, empresa=empresa)
        empresas_favoritos_total.labels(acao="adicionar").inc()
        return Response(status=status.HTTP_201_CREATED)

    @favoritar.mapping.delete
    def desfavoritar(self, request, pk: str | None = None):
        empresa = self.get_object()
        fav = FavoritoEmpresa.objects.filter(usuario=request.user, empresa=empresa, deleted=False).first()
        if fav:
            fav.soft_delete()
        empresas_favoritos_total.labels(acao="remover").inc()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def avaliacoes(self, request, pk: str | None = None):
        empresa = self.get_object()
        if request.user.organizacao != empresa.organizacao:
            return Response({"detail": "Usuário não pertence à organização."}, status=403)
        if AvaliacaoEmpresa.objects.filter(empresa=empresa, usuario=request.user, deleted=False).exists():
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

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def restaurar(self, request, pk: str | None = None):
        empresa = self.get_object()
        if not empresa.deleted:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not (request.user == empresa.usuario or request.user.user_type in {UserType.ADMIN, UserType.ROOT}):
            return Response(status=403)
        empresa.undelete()
        EmpresaChangeLog.objects.create(
            empresa=empresa,
            usuario=request.user,
            campo_alterado="deleted",
            valor_antigo="True",
            valor_novo="False",
        )
        empresas_restauradas_total.inc()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], permission_classes=[IsAuthenticated])
    def purgar(self, request, pk: str | None = None):
        empresa = self.get_object()
        if not empresa.deleted:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            return Response(status=403)
        EmpresaChangeLog.objects.create(
            empresa=empresa,
            usuario=request.user,
            campo_alterado="purge",
            valor_antigo="True",
            valor_novo="deleted",
        )
        empresas_purgadas_total.inc()
        empresa.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
