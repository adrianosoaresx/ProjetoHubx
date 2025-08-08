from __future__ import annotations

import csv
import io
import logging
import tablib
from django.core.cache import cache
from rest_framework.pagination import PageNumberPagination
from services.nucleos_metrics import (
    get_total_membros,
    get_total_suplentes,
    get_membros_por_status,
    get_taxa_participacao,
)

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo, ConviteNucleo
from .serializers import (
    CoordenadorSuplenteSerializer,
    NucleoSerializer,
    ParticipacaoNucleoSerializer,
    ConviteNucleoSerializer,
)
from .tasks import (
    notify_exportacao_membros,
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


class ConviteNucleoCreateAPIView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ConviteNucleoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        convite = ConviteNucleo.objects.create(**serializer.validated_data)
        out = ConviteNucleoSerializer(convite)
        return Response(out.data, status=status.HTTP_201_CREATED)


class AceitarConviteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token = request.query_params.get("token")
        convite = get_object_or_404(ConviteNucleo, token=token)
        if convite.usado_em or convite.expirado():
            return Response({"detail": _("Convite inválido ou expirado.")}, status=400)
        if request.user.email.lower() != convite.email.lower():
            return Response({"detail": _("Este convite não pertence a você.")}, status=403)
        ParticipacaoNucleo.objects.get_or_create(
            user=request.user,
            nucleo=convite.nucleo,
            defaults={
                "status": "ativo",
                "papel": convite.papel,
            },
        )
        convite.usado_em = timezone.now()
        convite.save(update_fields=["usado_em"])
        return Response({"detail": _("Convite aceito com sucesso.")})


class NucleoViewSet(viewsets.ModelViewSet):
    serializer_class = NucleoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NucleoPagination
    def get_queryset(self):
        return (
            Nucleo.objects.filter(deleted=False, ativo=True)
            .select_related("organizacao")
            .prefetch_related("coordenadores_suplentes")
        )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        org = request.query_params.get("organizacao")
        if org:
            queryset = queryset.filter(organizacao_id=org)
        page_number = request.query_params.get("page", "1")
        page_size = request.query_params.get("page_size", str(self.pagination_class.page_size))
        cache_key = f"nucleos_list_{org}_{page_number}_{page_size}"
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



    def perform_destroy(self, instance: Nucleo) -> None:
        instance.delete()

    @action(detail=True, methods=["post"], url_path="solicitar", permission_classes=[IsAuthenticated])
    def solicitar(self, request, pk: str | None = None):
        nucleo = self.get_object()
        participacao, created = ParticipacaoNucleo.objects.get_or_create(
            user=request.user, nucleo=nucleo
        )
        if not created:
            if participacao.status == "pendente":
                return Response({"detail": _("Já solicitado.")}, status=400)
            if participacao.status == "ativo":
                return Response({"detail": _("Já membro do núcleo.")}, status=400)
            participacao.status = "pendente"
            participacao.data_solicitacao = timezone.now()
            participacao.data_decisao = None
            participacao.decidido_por = None
            participacao.justificativa = ""
            participacao.deleted = False
            participacao.deleted_at = None
            participacao.save(
                update_fields=[
                    "status",
                    "data_solicitacao",
                    "data_decisao",
                    "decidido_por",
                    "justificativa",
                    "deleted",
                    "deleted_at",
                ]
            )
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
        participacao = get_object_or_404(
            ParticipacaoNucleo, nucleo=nucleo, user_id=user_id
        )
        if participacao.status != "pendente":
            return Response({"detail": _("Solicitação já decidida.")}, status=400)
        participacao.status = "ativo"
        participacao.data_decisao = timezone.now()
        participacao.decidido_por = request.user
        participacao.justificativa = ""
        participacao.save(
            update_fields=["status", "data_decisao", "decidido_por", "justificativa"]
        )
        logger.info("Participação aprovada", extra={"participacao_id": participacao.id, "decidido_por": request.user.id})
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
        participacao = get_object_or_404(
            ParticipacaoNucleo, nucleo=nucleo, user_id=user_id
        )
        if participacao.status != "pendente":
            return Response({"detail": _("Solicitação já decidida.")}, status=400)
        justificativa = request.data.get("justificativa", "")
        participacao.status = "inativo"
        participacao.data_decisao = timezone.now()
        participacao.decidido_por = request.user
        participacao.justificativa = justificativa
        participacao.save(
            update_fields=["status", "data_decisao", "decidido_por", "justificativa"]
        )
        logger.info(
            "Participação recusada",
            extra={"participacao_id": participacao.id, "decidido_por": request.user.id},
        )
        notify_participacao_recusada.delay(participacao.id)
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def participacoes(self, request, pk: str | None = None):
        nucleo = self.get_object()
        if ParticipacaoNucleo.objects.filter(user=request.user, nucleo=nucleo).exists():
            return Response({"detail": _("Já solicitado ou membro do núcleo.")}, status=400)
        participacao = ParticipacaoNucleo.objects.create(user=request.user, nucleo=nucleo)
        serializer = ParticipacaoNucleoSerializer(participacao)
        return Response(serializer.data, status=201)

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
        if not ParticipacaoNucleo.objects.filter(
            nucleo=nucleo, user=data["usuario"], status="ativo"
        ).exists():
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
        cache_key = f"nucleo_{nucleo.id}_membros_{page_number}_{page_size}"
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
        qs = nucleo.participacoes.select_related("user").filter(status="ativo")
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

    @action(
        detail=True,
        methods=["get"],
        url_path="membros/exportar",
        permission_classes=[IsAdminOrCoordenador],
    )
    def exportar_membros(self, request, pk: str | None = None):
        nucleo = self.get_object()
        formato = request.query_params.get("formato", "csv")
        membros = nucleo.participacoes.select_related("user").all()
        now = timezone.now()
        suplentes = set(
            CoordenadorSuplente.objects.filter(
                nucleo=nucleo,
                periodo_inicio__lte=now,
                periodo_fim__gte=now,
                deleted=False,
            ).values_list("usuario_id", flat=True)
        )
        data = tablib.Dataset(
            headers=[
                "Nome",
                "Email",
                "Status",
                "papel",
                "is_suplente",
                "data_ingresso",
            ]
        )
        for p in membros:
            nome = p.user.get_full_name() or p.user.username
            data.append(
                [
                    nome,
                    p.user.email,
                    p.status,
                    p.papel,
                    p.user_id in suplentes,
                    (p.data_decisao or p.data_solicitacao).isoformat(),
                ]
            )
        notify_exportacao_membros.delay(nucleo.id)
        logger.info(
            "Exportação de membros",
            extra={"nucleo_id": nucleo.id, "user_id": request.user.id, "formato": formato},
        )
        if formato == "xls":
            resp = HttpResponse(
                data.export("xlsx"),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = (
                f"attachment; filename=nucleo-{nucleo.id}-membros.xlsx"
            )
            return resp
        resp = HttpResponse(data.export("csv"), content_type="text/csv")
        resp["Content-Disposition"] = f"attachment; filename=nucleo-{nucleo.id}-membros.csv"
        return resp

    @action(detail=True, methods=["get"], url_path="metrics", permission_classes=[IsAuthenticated])
    def metrics(self, request, pk: str | None = None):
        nucleo = self.get_object()
        cache_key = f"nucleo_{nucleo.id}_metrics"
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

    @action(
        detail=False,
        methods=["get"],
        url_path="relatorio",
        permission_classes=[IsAdmin],
    )
    def relatorio(self, request):
        formato = request.query_params.get("formato", "csv")
        nucleos = Nucleo.objects.filter(deleted=False)
        from agenda.models import Evento

        dados = []
        for n in nucleos:
            membros = n.participacoes.filter(status="ativo").count()
            eventos = Evento.objects.filter(nucleo=n)
            datas = ";".join(
                e.data_inicio.isoformat() for e in eventos if getattr(e, "data_inicio", None)
            )
            dados.append([n.nome, membros, eventos.count(), datas])

        if formato == "pdf":
            from reportlab.pdfgen import canvas

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer)
            y = 800
            p.drawString(50, y, "Relatório de Núcleos")
            y -= 20
            for row in dados:
                p.drawString(
                    50, y, f"{row[0]} - Membros: {row[1]} Eventos: {row[2]} Datas: {row[3]}"
                )
                y -= 20
            p.showPage()
            p.save()
            buffer.seek(0)
            resp = HttpResponse(buffer.getvalue(), content_type="application/pdf")
            resp["Content-Disposition"] = "attachment; filename=relatorio-nucleos.pdf"
            return resp

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Núcleo", "Membros", "Eventos", "Datas"])
        for row in dados:
            writer.writerow(row)
        resp = HttpResponse(output.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=relatorio-nucleos.csv"
        return resp
