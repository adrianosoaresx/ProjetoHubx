from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

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


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
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


class PushSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.update_or_create(
            user=request.user, token=serializer.validated_data["token"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token required"}, status=status.HTTP_400_BAD_REQUEST)
        PushSubscription.objects.filter(user=request.user, token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
