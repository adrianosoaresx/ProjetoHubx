from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConfiguracaoConta
from .serializers import ConfiguracaoContaSerializer


class ConfiguracaoContaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self) -> ConfiguracaoConta:
        obj, _ = ConfiguracaoConta.objects.get_or_create(user=self.request.user)
        return obj

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
