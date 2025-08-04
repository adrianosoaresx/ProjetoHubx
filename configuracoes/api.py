from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConfiguracaoConta
from .serializers import ConfiguracaoContaSerializer
from .services import get_configuracao_conta


class ConfiguracaoContaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self) -> ConfiguracaoConta:
        return get_configuracao_conta(self.request.user)

    def get(self, request):
        serializer = ConfiguracaoContaSerializer(self.get_object())
        return Response(serializer.data)

    def put(self, request):
        obj = self.get_object()
        serializer = ConfiguracaoContaSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        obj = self.get_object()
        serializer = ConfiguracaoContaSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
