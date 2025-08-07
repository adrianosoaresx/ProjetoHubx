from __future__ import annotations

import csv
import io
import logging
import tablib

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


class IsAdminOrCoordenador(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tipo = request.user.get_tipo_usuario
        return tipo in {"admin", "coordenador", "root"}


class IsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tipo = request.user.get_tipo_usuario
        return tipo in {"admin", "root"}


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
                "status": "aprovado",
                "is_coordenador": convite.papel == "coordenador",
            },
        )
        convite.usado_em = timezone.now()
        convite.save(update_fields=["usado_em"])
        return Response({"detail": _("Convite aceito com sucesso.")})


class NucleoViewSet(viewsets.ModelViewSet):
    queryset = Nucleo.objects.filter(deleted=False)
    serializer_class = NucleoSerializer
    permission_classes = [IsAuthenticated]

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
            if participacao.status == "aprovado":
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
        participacao.status = "aprovado"
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
        participacao.status = "recusado"
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
            novo_status = "aprovado"
        elif acao == "reject":
            novo_status = "recusado"
        else:
            return Response({"detail": _("Ação inválida.")}, status=400)
        if participacao.status != "pendente":
            return Response({"detail": _("Solicitação já decidida.")}, status=400)
        participacao.status = novo_status
        participacao.data_decisao = timezone.now()
        participacao.decidido_por = request.user
        participacao.save(update_fields=["status", "data_decisao", "decidido_por"])
        if novo_status == "aprovado":
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
            nucleo=nucleo, user=data["usuario"], status="aprovado"
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
                "is_coordenador",
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
                    p.is_coordenador,
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
            membros = n.participacoes.filter(status="aprovado").count()
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
