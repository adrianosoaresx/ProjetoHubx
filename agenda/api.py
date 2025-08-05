from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Q

from accounts.models import UserType
from .models import (
    BriefingEvento,
    Evento,
    EventoLog,
    InscricaoEvento,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
)
from .serializers import (
    BriefingEventoSerializer,
    EventoSerializer,
    InscricaoEventoSerializer,
    MaterialDivulgacaoEventoSerializer,
    ParceriaEventoSerializer,
)
from .tasks import notificar_briefing_status


class DefaultPagination(PageNumberPagination):
    page_size = 10


class OrganizacaoFilterMixin:
    """Filtra objetos pela organização do usuário."""

    def filter_by_organizacao(self, qs, evento_field: str | None = None):
        user = self.request.user
        if getattr(user, "user_type", None) == UserType.ROOT:
            return qs
        prefix = f"{evento_field}__" if evento_field else ""
        nucleo_ids = list(user.nucleos.values_list("id", flat=True))
        filtro = Q(**{f"{prefix}organizacao": user.organizacao})
        if nucleo_ids:
            filtro |= Q(**{f"{prefix}nucleo__in": nucleo_ids})
        return qs.filter(filtro)


class EventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = EventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    queryset = Evento.objects.select_related("organizacao", "nucleo").all()

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self.filter_by_organizacao(qs)
        ordering = self.request.query_params.get("ordering")
        if ordering in {"data_inicio", "-data_inicio", "data_fim", "-data_fim"}:
            qs = qs.order_by(ordering)
        return qs

    def perform_destroy(self, instance: Evento) -> None:
        instance.soft_delete()


class InscricaoEventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = InscricaoEventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = InscricaoEvento.objects.select_related("evento", "user")
        qs = self.filter_by_organizacao(qs, "evento")
        evento = self.request.query_params.get("evento")
        if evento:
            qs = qs.filter(evento_id=evento)
        return qs.order_by("-created")

    def perform_destroy(self, instance: InscricaoEvento) -> None:
        instance.soft_delete()


class MaterialDivulgacaoEventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = MaterialDivulgacaoEventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = MaterialDivulgacaoEvento.objects.select_related("evento")
        qs = self.filter_by_organizacao(qs, "evento")
        return qs.order_by("-created")

    def perform_destroy(self, instance: MaterialDivulgacaoEvento) -> None:
        instance.soft_delete()


class ParceriaEventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = ParceriaEventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination
    queryset = ParceriaEvento.objects.select_related("evento", "empresa", "nucleo").all()

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self.filter_by_organizacao(qs, "evento")
        return qs

    def perform_destroy(self, instance: ParceriaEvento) -> None:
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def avaliar(self, request, pk=None):
        parceria = self.get_object()
        if parceria.avaliacao is not None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            parceria.avaliacao = int(request.data.get("avaliacao"))
        except (TypeError, ValueError):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        parceria.comentario = request.data.get("comentario", "")
        parceria.save(update_fields=["avaliacao", "comentario", "modified"])
        return Response(self.get_serializer(parceria).data)


class BriefingEventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = BriefingEventoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = BriefingEvento.objects.select_related("evento")
        qs = self.filter_by_organizacao(qs, "evento")
        return qs

    def perform_destroy(self, instance: BriefingEvento) -> None:
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def orcamentar(self, request, pk=None):
        briefing = self.get_object()
        briefing.status = "orcamentado"
        briefing.orcamento_enviado_em = timezone.now()
        prazo = request.data.get("prazo_limite_resposta")
        if prazo:
            briefing.prazo_limite_resposta = prazo
        briefing.save(update_fields=["status", "orcamento_enviado_em", "prazo_limite_resposta", "modified"])
        EventoLog.objects.create(
            evento=briefing.evento,
            usuario=request.user,
            acao="briefing_orcamentado",
        )
        notificar_briefing_status.delay(briefing.pk, briefing.status)
        return Response(self.get_serializer(briefing).data)

    @action(detail=True, methods=["post"])
    def aprovar(self, request, pk=None):
        briefing = self.get_object()
        briefing.status = "aprovado"
        briefing.aprovado_em = timezone.now()
        briefing.coordenadora_aprovou = True
        briefing.save(update_fields=["status", "aprovado_em", "coordenadora_aprovou", "modified"])
        EventoLog.objects.create(
            evento=briefing.evento,
            usuario=request.user,
            acao="briefing_aprovado",
        )
        notificar_briefing_status.delay(briefing.pk, briefing.status)
        return Response(self.get_serializer(briefing).data)

    @action(detail=True, methods=["post"])
    def recusar(self, request, pk=None):
        briefing = self.get_object()
        briefing.status = "recusado"
        briefing.motivo_recusa = request.data.get("motivo_recusa", "")
        briefing.recusado_em = timezone.now()
        briefing.recusado_por = request.user
        briefing.save(
            update_fields=[
                "status",
                "motivo_recusa",
                "recusado_em",
                "recusado_por",
                "modified",
            ]
        )
        EventoLog.objects.create(
            evento=briefing.evento,
            usuario=request.user,
            acao="briefing_recusado",
            detalhes={"motivo_recusa": briefing.motivo_recusa},
        )
        notificar_briefing_status.delay(briefing.pk, briefing.status)
        return Response(self.get_serializer(briefing).data)
