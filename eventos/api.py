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

from .models import Evento, EventoLog, FeedbackNota, InscricaoEvento
from .permissions import IsAdminOrCoordenadorOrReadOnly
from .serializers import EventoSerializer, InscricaoEventoSerializer


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

