from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Canal, NotificationLog, NotificationStatus, NotificationTemplate, PushSubscription
from .permissions import CanSendNotifications
from .serializers import (
    NotificationLogSerializer,
    NotificationTemplateSerializer,
    PushSubscriptionSerializer,
)
from .services.notificacoes import enviar_para_usuario


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


class NotificationLogViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = NotificationLog.objects.select_related("template").order_by("-data_envio")
        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(user=user)
        canal = self.request.query_params.get("canal")
        status_param = self.request.query_params.get("status")
        inicio = self.request.query_params.get("inicio")
        fim = self.request.query_params.get("fim")
        if canal in Canal.values:
            qs = qs.filter(canal=canal)
        if status_param in NotificationStatus.values:
            qs = qs.filter(status=status_param)
        if inicio:
            qs = qs.filter(data_envio__date__gte=inicio)
        if fim:
            qs = qs.filter(data_envio__date__lte=fim)
        return qs

    def partial_update(self, request, *args, **kwargs):
        if request.data.get("status") != NotificationStatus.LIDA:
            return Response({"detail": _("Status inválido")}, status=status.HTTP_400_BAD_REQUEST)
        log = self.get_object()
        log.status = NotificationStatus.LIDA
        log.data_leitura = timezone.now()
        log.save(update_fields=["status", "data_leitura"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([CanSendNotifications])
def enviar_view(request):
    template_codigo = request.data.get("template_codigo")
    user_id = request.data.get("user_id")
    context = request.data.get("context", {})
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Usuário não encontrado"}, status=status.HTTP_404_NOT_FOUND)
    try:
        enviar_para_usuario(user, template_codigo, context)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_204_NO_CONTENT)



class PushSubscriptionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user, ativo=True)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = PushSubscriptionSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, created = PushSubscription.all_objects.update_or_create(
            user=request.user,
            device_id=serializer.validated_data["device_id"],
            defaults={
                "endpoint": serializer.validated_data["endpoint"],
                "p256dh": serializer.validated_data["p256dh"],
                "auth": serializer.validated_data["auth"],
                "ativo": True,
                "deleted": False,
                "deleted_at": None,
            },
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(PushSubscriptionSerializer(subscription).data, status=status_code)

    def destroy(self, request, pk=None):
        try:
            subscription = self.get_queryset().get(pk=pk)
        except PushSubscription.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        subscription.ativo = False
        subscription.save(update_fields=["ativo"])
        return Response(status=status.HTTP_204_NO_CONTENT)
