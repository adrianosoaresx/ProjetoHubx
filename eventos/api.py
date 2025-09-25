from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from accounts.models import UserType

from .models import (
    BriefingEvento,
    Evento,
    EventoLog,
    FeedbackNota,
    InscricaoEvento,
    ParceriaEvento,
)
from .permissions import IsAdminOrCoordenadorOrReadOnly
from .serializers import (
    BriefingEventoSerializer,
    EventoSerializer,
    InscricaoEventoSerializer,
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
    permission_classes = [IsAdminOrCoordenadorOrReadOnly]
    pagination_class = DefaultPagination
    queryset = Evento.objects.select_related("organizacao", "nucleo").all()

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self.filter_by_organizacao(qs)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(titulo__icontains=search)
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
        return qs.order_by("-created_at")

    def perform_destroy(self, instance: InscricaoEvento) -> None:
        try:
            instance.cancelar_inscricao()
        except ValueError as exc:
            raise ValidationError(str(exc))

    @action(detail=True, methods=["post"])
    def avaliar(self, request, pk=None):
        inscricao = self.get_object()
        if inscricao.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if FeedbackNota.objects.filter(evento=inscricao.evento, usuario=request.user).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if timezone.now() <= inscricao.evento.data_fim:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            nota = int(request.data.get("nota"))
        except (TypeError, ValueError):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if nota < 1 or nota > 5:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        FeedbackNota.objects.create(
            evento=inscricao.evento,
            usuario=request.user,
            nota=nota,
            comentario=request.data.get("feedback", ""),
        )
        return Response(self.get_serializer(inscricao).data, status=status.HTTP_200_OK)


class ParceriaEventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = ParceriaEventoSerializer
    permission_classes = [IsAdminOrCoordenadorOrReadOnly]
    pagination_class = DefaultPagination
    queryset = ParceriaEvento.objects.select_related("evento", "nucleo").all()

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self.filter_by_organizacao(qs, "evento")
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=self.request.user,
            acao="parceria_criada",
            detalhes={"parceria": instance.pk},
        )

    def perform_update(self, serializer):
        old_instance = ParceriaEvento.all_objects.get(pk=serializer.instance.pk)
        instance = serializer.save()
        changes = {}
        for field, value in serializer.validated_data.items():
            before = getattr(old_instance, field)
            after = getattr(instance, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=self.request.user,
            acao="parceria_atualizada",
            detalhes=changes,
        )

    def perform_destroy(self, instance: ParceriaEvento) -> None:
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=self.request.user,
            acao="parceria_excluida",
            detalhes={"parceria": instance.pk},
        )
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def avaliar(self, request, pk=None):
        parceria = self.get_object()
        if parceria.avaliacao is not None:
            return Response(
                {"error": "Parceria já avaliada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            parceria.avaliacao = int(request.data.get("avaliacao"))
        except (TypeError, ValueError):
            return Response(
                {"error": "Avaliação inválida."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parceria.comentario = request.data.get("comentario", "")
        parceria.save(update_fields=["avaliacao", "comentario", "updated_at"])
        EventoLog.objects.create(
            evento=parceria.evento,
            usuario=request.user,
            acao="parceria_avaliada",
            detalhes={
                "parceria": parceria.pk,
                "avaliacao": parceria.avaliacao,
                "comentario": parceria.comentario,
            },
        )
        data = self.get_serializer(parceria).data
        data["success"] = "Avaliação registrada com sucesso."
        return Response(data)


class BriefingEventoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    serializer_class = BriefingEventoSerializer
    permission_classes = [IsAdminOrCoordenadorOrReadOnly]
    pagination_class = DefaultPagination

    def get_queryset(self):
        qs = BriefingEvento.objects.select_related("evento")
        qs = self.filter_by_organizacao(qs, "evento")
        return qs

    def perform_destroy(self, instance: BriefingEvento) -> None:
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=self.request.user,
            acao="briefing_excluido",
            detalhes={"briefing": instance.pk},
        )
        instance.soft_delete()

    @action(detail=True, methods=["post"])
    def orcamentar(self, request, pk=None):
        briefing = self.get_object()
        if not briefing.can_transition_to("orcamentado"):
            return Response({"detail": _("Transição de status inválida.")}, status=status.HTTP_400_BAD_REQUEST)
        briefing.status = "orcamentado"
        briefing.orcamento_enviado_em = timezone.now()
        prazo = request.data.get("prazo_limite_resposta")
        if prazo:
            briefing.prazo_limite_resposta = prazo
        briefing.save(update_fields=["status", "orcamento_enviado_em", "prazo_limite_resposta", "updated_at"])
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
        if not briefing.can_transition_to("aprovado"):
            return Response({"detail": _("Transição de status inválida.")}, status=status.HTTP_400_BAD_REQUEST)
        briefing.status = "aprovado"
        briefing.aprovado_em = timezone.now()
        briefing.coordenadora_aprovou = True
        briefing.save(update_fields=["status", "aprovado_em", "coordenadora_aprovou", "updated_at"])
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
        if not briefing.can_transition_to("recusado"):
            return Response({"detail": _("Transição de status inválida.")}, status=status.HTTP_400_BAD_REQUEST)
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
                "updated_at",
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
