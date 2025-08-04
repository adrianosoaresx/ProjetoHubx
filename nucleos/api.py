from __future__ import annotations

import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from .serializers import (
    CoordenadorSuplenteSerializer,
    NucleoSerializer,
    ParticipacaoNucleoSerializer,
)
from .tasks import (
    notify_exportacao_membros,
    notify_participacao_aprovada,
    notify_participacao_recusada,
    notify_suplente_designado,
)


class IsAdminOrCoordenador(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tipo = request.user.get_tipo_usuario
        return tipo in {"admin", "coordenador", "root"}


class NucleoViewSet(viewsets.ModelViewSet):
    queryset = Nucleo.objects.filter(deleted=False)
    serializer_class = NucleoSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance: Nucleo) -> None:
        instance.delete()

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
        methods=["post"],
        url_path="coordenadores-suplentes",
        permission_classes=[IsAdminOrCoordenador],
    )
    def adicionar_suplente(self, request, pk: str | None = None):
        nucleo = self.get_object()
        serializer = CoordenadorSuplenteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["periodo_inicio"] >= data["periodo_fim"]:
            return Response({"detail": _("Período inválido.")}, status=400)
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
        url_path="coordenadores-suplentes/(?P<suplente_id>[^/.]+)",
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
        url_path="exportar-membros",
        permission_classes=[IsAdminOrCoordenador],
    )
    def exportar_membros(self, request, pk: str | None = None):
        nucleo = self.get_object()
        membros = nucleo.participacoes.select_related("user").all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Nome", "Email", "Status", "Função"])
        for p in membros:
            funcao = _("Coordenador") if p.is_coordenador else _("Membro")
            nome = p.user.get_full_name() or p.user.username
            writer.writerow([nome, p.user.email, p.status, funcao])
        notify_exportacao_membros.delay(nucleo.id)
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=nucleo-{nucleo.id}-membros.csv"
        return response
