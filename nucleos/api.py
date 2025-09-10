from __future__ import annotations

import logging
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cache import get_cache_version
from feed.api import NucleoPostSerializer
from financeiro import atualizar_cobranca
from services.nucleos import user_belongs_to_nucleo
from services.nucleos_metrics import (
    get_membros_por_status,
    get_taxa_participacao,
    get_total_membros,
    get_total_suplentes,
)

from .metrics import convites_usados_total, membros_suspensos_total
from .models import ConviteNucleo, CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from .serializers import (
    ConviteNucleoSerializer,
    CoordenadorSuplenteSerializer,
    NucleoSerializer,
    ParticipacaoNucleoSerializer,
)
from .services import gerar_convite_nucleo, registrar_uso_convite
from .tasks import (
    notify_participacao_aprovada,
    notify_participacao_recusada,
    notify_suplente_designado,
)

logger = logging.getLogger(__name__)


class NucleoPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsAdminOrCoordenador(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tipo = request.user.get_tipo_usuario
        return tipo in {"admin", "coordenador", "root"}

    def has_object_permission(self, request, view, obj):
        org = getattr(obj, "organizacao", None)
        if org is None and hasattr(obj, "nucleo"):
            org = obj.nucleo.organizacao
        if org and org != request.user.organizacao:
            return False
        return self.has_permission(request, view)


class IsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tipo = request.user.get_tipo_usuario
        return tipo in {"admin", "root"}

    def has_object_permission(self, request, view, obj):
        org = getattr(obj, "organizacao", None)
        if org is None and hasattr(obj, "nucleo"):
            org = obj.nucleo.organizacao
        if org and org != request.user.organizacao:
            return False
        return self.has_permission(request, view)


class AceitarConviteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token = request.query_params.get("token")
        convite = get_object_or_404(ConviteNucleo, token=token)
        if convite.usado_em is not None:
            return Response({"detail": _("Convite já utilizado.")}, status=400)
        if convite.expirado():
            return Response({"detail": _("Convite inválido ou expirado.")}, status=400)
        if request.user.email.lower() != convite.email.lower():
            return Response({"detail": _("Este convite não pertence a você.")}, status=403)
        nucleo = convite.nucleo
        if request.user.organizacao_id != nucleo.organizacao_id:
            return Response(
                {"detail": _("Você não tem permissão para acessar este núcleo.")},
                status=403,
            )
        try:
            registrar_uso_convite(convite)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        ParticipacaoNucleo.objects.get_or_create(
            user=request.user,
            nucleo=nucleo,
            defaults={
                "status": "ativo",
                "papel": convite.papel,
            },
        )
        convite.usado_em = timezone.now()
        convite.save(update_fields=["usado_em"])
        convites_usados_total.inc()
        logger.info(
            "convite_usado",
            extra={
                "convite_id": str(convite.pk),
                "nucleo_id": str(convite.nucleo_id),  # type: ignore[attr-defined]
                "user_id": str(request.user.pk),
            },
        )
        return Response({"detail": _("Convite aceito com sucesso.")})


class NucleoViewSet(viewsets.ModelViewSet):
    serializer_class = NucleoSerializer
    permission_classes = [IsAdminOrCoordenador]
    pagination_class = NucleoPagination

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            perms = [IsAdmin]
        else:
            perms = self.permission_classes
        return [p() for p in perms]

    def get_queryset(self):
        qs = (
            Nucleo.objects.filter(deleted=False)
            .select_related("organizacao")
            .prefetch_related("coordenadores_suplentes")
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(nome__icontains=search)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        org_param = request.query_params.get("organizacao")
        user_org_id = str(getattr(request.user, "organizacao_id", "") or "")
        if org_param and org_param != user_org_id:
            return Response(
                {"detail": _("Você não tem permissão para acessar esta organização.")},
                status=status.HTTP_403_FORBIDDEN,
            )
        org = org_param or user_org_id
        if org:
            queryset = queryset.filter(organizacao_id=org)
        page_number = request.query_params.get("page", "1")
        page_size = request.query_params.get("page_size", str(self.pagination_class.page_size))
        search = request.query_params.get("search")
        version = get_cache_version(f"nucleos_list_{org}")
        cache_key = f"nucleos_list_{org}_v{version}_{page_number}_{page_size}_{search or ''}"
        data = cache.get(cache_key)
        if data is not None:
            resp = Response(data)
            resp["X-Cache"] = "HIT"
            return resp
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        response = self.get_paginated_response(serializer.data)
        cache.set(cache_key, response.data, 300)
        response["X-Cache"] = "MISS"
        return response

    @action(
        detail=False,
        methods=["get"],
        url_path="meus",
        permission_classes=[IsAuthenticated],
    )
    def meus(self, request):
        qs = self.get_queryset().filter(
            participacoes__user=request.user,
            participacoes__status="ativo",
            participacoes__status_suspensao=False,
        )
        qs = qs.distinct()
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def perform_destroy(self, instance: Nucleo) -> None:
        instance.delete()

    @action(
        detail=True,
        methods=["post"],
        url_path="convites",
        permission_classes=[IsAdmin],
    )
    def convites(self, request, pk: str | None = None):
        nucleo = self.get_object()
        data = request.data.copy()
        data["nucleo"] = nucleo.pk
        serializer = ConviteNucleoSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            convite = gerar_convite_nucleo(
                request.user,
                nucleo,
                serializer.validated_data["email"],
                serializer.validated_data["papel"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        out = ConviteNucleoSerializer(convite)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path="convites/(?P<convite_id>[^/.]+)",
        permission_classes=[IsAdmin],
    )
    def revogar_convite(self, request, pk: str | None = None, convite_id: str | None = None):
        nucleo = self.get_object()
        convite = get_object_or_404(ConviteNucleo, pk=convite_id, nucleo=nucleo)
        agora = timezone.now()
        convite.data_expiracao = agora
        convite.usado_em = agora
        convite.save(update_fields=["data_expiracao", "usado_em"])
        logger.info(
            "convite_revogado",
            extra={
                "convite_id": str(convite.pk),
                "nucleo_id": str(nucleo.pk),
                "user_id": str(request.user.pk),
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="posts", permission_classes=[IsAuthenticated])
    def posts(self, request, pk: str | None = None):
        nucleo = self.get_object()
        eh_membro = ParticipacaoNucleo.objects.filter(
            user=request.user,
            nucleo=nucleo,
            status="ativo",
            status_suspensao=False,
        ).exists()
        if not eh_membro:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = NucleoPostSerializer(
            data=request.data,
            context={"nucleo": nucleo},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(
            autor=request.user,
            organizacao=nucleo.organizacao,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="solicitar", permission_classes=[IsAuthenticated])
    def solicitar(self, request, pk: str | None = None):
        nucleo = self.get_object()
        if request.user.organizacao_id != nucleo.organizacao_id:
            return Response(
                {"detail": _("Você não tem permissão para acessar este núcleo.")},
                status=403,
            )
        participacao, created = ParticipacaoNucleo.all_objects.get_or_create(user=request.user, nucleo=nucleo)

        save_fields: list[str] = []
        if participacao.deleted:
            participacao.deleted = False
            participacao.deleted_at = None
            save_fields += ["deleted", "deleted_at"]

        if not created:
            if not save_fields:
                if participacao.status == "pendente":
                    return Response({"detail": _("Já solicitado.")}, status=400)
                if participacao.status == "ativo":
                    return Response({"detail": _("Já membro do núcleo.")}, status=400)
            participacao.status = "pendente"
            participacao.data_solicitacao = timezone.now()
            participacao.data_decisao = None
            participacao.decidido_por = None
            participacao.justificativa = ""
            save_fields += [
                "status",
                "data_solicitacao",
                "data_decisao",
                "decidido_por",
                "justificativa",
            ]

        if save_fields:
            participacao.save(update_fields=save_fields)

        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="membros/(?P<user_id>[^/.]+)/aprovar",
        permission_classes=[IsAdminOrCoordenador],
    )
    def aprovar_membro(self, request, pk: str | None = None, user_id: str | None = None):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, nucleo=nucleo, user_id=user_id)
        if participacao.status != "pendente":
            return Response({"detail": _("Solicitação já decidida.")}, status=400)
        participacao.status = "ativo"
        participacao.data_decisao = timezone.now()
        participacao.decidido_por = request.user
        participacao.justificativa = ""
        participacao.save(update_fields=["status", "data_decisao", "decidido_por", "justificativa"])
        logger.info(
            "Participação aprovada", extra={"participacao_id": participacao.id, "decidido_por": request.user.id}
        )
        notify_participacao_aprovada.delay(participacao.id)
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="membros/(?P<user_id>[^/.]+)/recusar",
        permission_classes=[IsAdminOrCoordenador],
    )
    def recusar_membro(self, request, pk: str | None = None, user_id: str | None = None):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, nucleo=nucleo, user_id=user_id)
        if participacao.status != "pendente":
            return Response({"detail": _("Solicitação já decidida.")}, status=400)
        justificativa = request.data.get("justificativa", "")
        participacao.status = "inativo"
        participacao.data_decisao = timezone.now()
        participacao.decidido_por = request.user
        participacao.justificativa = justificativa
        participacao.save(update_fields=["status", "data_decisao", "decidido_por", "justificativa"])
        logger.info(
            "Participação recusada",
            extra={"participacao_id": participacao.id, "decidido_por": request.user.id},
        )
        notify_participacao_recusada.delay(participacao.id)
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="membros/(?P<user_id>[^/.]+)/suspender",
        permission_classes=[IsAdminOrCoordenador],
    )
    def suspender_membro(self, request, pk: str | None = None, user_id: str | None = None):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, nucleo=nucleo, user_id=user_id, status="ativo")
        if participacao.status_suspensao:
            return Response({"detail": _("Membro já suspenso.")}, status=400)
        participacao.status_suspensao = True
        participacao.data_suspensao = timezone.now()
        participacao.save(update_fields=["status_suspensao", "data_suspensao"])
        atualizar_cobranca(nucleo.id, participacao.user_id, "inativo")
        membros_suspensos_total.inc()
        logger.info(
            "membro_suspenso",
            extra={
                "nucleo_id": str(nucleo.pk),
                "user_id": str(participacao.user_id),  # type: ignore[attr-defined]
                "suspendido_em": participacao.data_suspensao.isoformat(),
            },
        )
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="membros/(?P<user_id>[^/.]+)/reativar",
        permission_classes=[IsAdminOrCoordenador],
    )
    def reativar_membro(self, request, pk: str | None = None, user_id: str | None = None):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, nucleo=nucleo, user_id=user_id)
        if not participacao.status_suspensao:
            return Response({"detail": _("Membro não está suspenso.")}, status=400)
        participacao.status_suspensao = False
        participacao.data_suspensao = None
        participacao.save(update_fields=["status_suspensao", "data_suspensao"])
        atualizar_cobranca(nucleo.id, participacao.user_id, "ativo")
        logger.info(
            "membro_reativado",
            extra={
                "nucleo_id": str(nucleo.pk),
                "user_id": str(participacao.user_id),  # type: ignore[attr-defined]
            },
        )
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "patch", "delete"],
        url_path="membros/(?P<user_id>[^/.]+)/coordenador",
        permission_classes=[IsAdminOrCoordenador],
    )
    def coordenador(
        self,
        request,
        pk: str | None = None,
        user_id: str | None = None,
    ):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, nucleo=nucleo, user_id=user_id, status="ativo")
        if request.method == "POST":
            if participacao.papel == "coordenador":
                return Response({"detail": _("Membro já é coordenador.")}, status=400)
            participacao.papel = "coordenador"
            participacao.save(update_fields=["papel"])
            serializer = ParticipacaoNucleoSerializer(participacao)
            return Response(serializer.data)
        if request.method == "PATCH":
            if participacao.papel != "coordenador":
                return Response({"detail": _("Membro não é coordenador.")}, status=400)
            participacao.papel = "membro"
            participacao.save(update_fields=["papel"])
            serializer = ParticipacaoNucleoSerializer(participacao)
            return Response(serializer.data)
        if participacao.papel != "coordenador":
            return Response({"detail": _("Membro não é coordenador.")}, status=400)
        participacao.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="membros/(?P<user_id>[^/.]+)/promover",
        permission_classes=[IsAdminOrCoordenador],
    )
    def promover_membro(
        self,
        request,
        pk: str | None = None,
        user_id: str | None = None,
    ):
        return self.coordenador(request, pk=pk, user_id=user_id)

    @action(
        detail=True,
        methods=["delete"],
        url_path="membros/(?P<user_id>[^/.]+)/remover",
        permission_classes=[IsAdminOrCoordenador],
    )
    def remover_membro(
        self,
        request,
        pk: str | None = None,
        user_id: str | None = None,
    ):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, nucleo=nucleo, user_id=user_id, status="ativo")
        user_pk = participacao.user_id
        participacao.delete()
        atualizar_cobranca(nucleo.id, user_pk, "inativo")
        logger.info(
            "membro_removido",
            extra={
                "nucleo_id": str(nucleo.pk),
                "user_id": str(user_pk),
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["get"],
        url_path="membro-status",
        permission_classes=[IsAuthenticated],
    )
    def membro_status(self, request, pk: str | None = None):
        nucleo = self.get_object()
        participa, info, suspenso = user_belongs_to_nucleo(request.user, nucleo.id)
        papel = ""
        ativo = False
        if participa:
            papel, status = info.split(":")
            ativo = status == "ativo"
        return Response({"papel": papel, "ativo": ativo, "suspenso": suspenso})

    @action(
        detail=True,
        methods=["patch"],
        url_path="participacoes/(?P<participacao_id>[^/.]+)",
        permission_classes=[IsAdminOrCoordenador],
    )
    def decidir_participacao(self, request, pk: str | None = None, participacao_id: str | None = None):
        nucleo = self.get_object()
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        acao = request.data.get("acao")
        if acao == "approve":
            novo_status = "ativo"
        elif acao == "reject":
            novo_status = "inativo"
        else:
            return Response({"detail": _("Ação inválida.")}, status=400)
        if participacao.status != "pendente":
            return Response({"detail": _("Solicitação já decidida.")}, status=400)
        participacao.status = novo_status
        participacao.data_decisao = timezone.now()
        participacao.decidido_por = request.user
        participacao.save(update_fields=["status", "data_decisao", "decidido_por"])
        if novo_status == "ativo":
            notify_participacao_aprovada.delay(participacao.id)
        else:
            notify_participacao_recusada.delay(participacao.id)
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="suplentes",
        permission_classes=[IsAdminOrCoordenador],
    )
    def suplentes(self, request, pk: str | None = None):
        nucleo = self.get_object()
        if request.method == "GET":
            qs = nucleo.coordenadores_suplentes.all()
            serializer = CoordenadorSuplenteSerializer(qs, many=True)
            return Response(serializer.data)
        serializer = CoordenadorSuplenteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["periodo_inicio"] >= data["periodo_fim"]:
            return Response({"detail": _("Período inválido.")}, status=400)
        if not ParticipacaoNucleo.objects.filter(nucleo=nucleo, user=data["usuario"], status="ativo").exists():
            return Response({"detail": _("Usuário não é membro do núcleo.")}, status=400)
        overlap = CoordenadorSuplente.objects.filter(
            nucleo=nucleo,
            usuario=data["usuario"],
            deleted=False,
            periodo_inicio__lt=data["periodo_fim"],
            periodo_fim__gt=data["periodo_inicio"],
        ).exists()
        if overlap:
            return Response({"detail": _("Usuário já é suplente no período informado.")}, status=400)
        suplente = CoordenadorSuplente.objects.create(
            nucleo=nucleo,
            usuario=data["usuario"],
            periodo_inicio=data["periodo_inicio"],
            periodo_fim=data["periodo_fim"],
        )
        notify_suplente_designado.delay(nucleo.id, suplente.usuario.email)
        out = CoordenadorSuplenteSerializer(suplente)
        return Response(out.data, status=201)

    @action(
        detail=True,
        methods=["delete"],
        url_path="suplentes/(?P<suplente_id>[^/.]+)",
        permission_classes=[IsAdminOrCoordenador],
    )
    def remover_suplente(self, request, pk: str | None = None, suplente_id: str | None = None):
        nucleo = self.get_object()
        suplente = get_object_or_404(CoordenadorSuplente, pk=suplente_id, nucleo=nucleo)
        suplente.delete()
        return Response(status=204)

    @action(detail=True, methods=["get"], url_path="membros", permission_classes=[IsAdminOrCoordenador])
    def membros(self, request, pk: str | None = None):
        nucleo = self.get_object()
        page_number = request.query_params.get("page", "1")
        page_size = request.query_params.get("page_size", str(self.pagination_class.page_size))
        version = get_cache_version(f"nucleo_{nucleo.id}_membros")
        cache_key = f"nucleo_{nucleo.id}_membros_v{version}_{page_number}_{page_size}"
        data = cache.get(cache_key)
        if data is not None:
            resp = Response(data)
            resp["X-Cache"] = "HIT"
            return resp
        qs = nucleo.participacoes.select_related("user").filter(deleted=False)
        page = self.paginate_queryset(qs)
        serializer = ParticipacaoNucleoSerializer(page, many=True)
        response = self.get_paginated_response(serializer.data)
        cache.set(cache_key, response.data, 300)
        response["X-Cache"] = "MISS"
        return response

    @action(
        detail=True,
        methods=["get"],
        url_path="membros-ativos",
        permission_classes=[IsAdminOrCoordenador],
    )
    def membros_ativos(self, request, pk: str | None = None):
        nucleo = self.get_object()
        qs = nucleo.participacoes.select_related("user").filter(status="ativo", status_suspensao=False)
        page = self.paginate_queryset(qs)
        data = [
            {
                "user_id": p.user_id,
                "papel": p.papel,
                "data_ingresso": (p.data_decisao or p.data_solicitacao),
                "mensalidade": nucleo.mensalidade,
            }
            for p in page
        ]
        return self.get_paginated_response(data)

    @action(detail=True, methods=["get"], url_path="metrics", permission_classes=[IsAuthenticated])
    def metrics(self, request, pk: str | None = None):
        nucleo = self.get_object()
        version = get_cache_version(f"nucleo_{nucleo.id}_metrics")
        cache_key = f"nucleo_{nucleo.id}_metrics_v{version}"
        data = cache.get(cache_key)
        from_cache = True
        if data is None:
            from_cache = False
            data = {
                "total_membros": get_total_membros(nucleo.id),
                "total_suplentes": get_total_suplentes(nucleo.id),
                "taxa_participacao": get_taxa_participacao(nucleo.organizacao_id),
            }
            if request.user.get_tipo_usuario in {"admin", "coordenador", "root"}:
                data["membros_por_status"] = get_membros_por_status(nucleo.id)
            cache.set(cache_key, data, 300)
        response = Response(data)
        response["X-Cache"] = "HIT" if from_cache else "MISS"
        logger.info("metrics accessed", extra={"nucleo_id": nucleo.id, "user_id": request.user.id})
        return response
