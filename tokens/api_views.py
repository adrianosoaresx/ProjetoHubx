from __future__ import annotations

import hashlib
from datetime import timedelta

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ApiToken, ApiTokenIp, ApiTokenLog
from .serializers import ApiTokenIpSerializer, ApiTokenSerializer
from .services import generate_token, list_tokens
from .utils import get_client_ip, revoke_token, rotate_token


class ApiTokenViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        tokens = list_tokens(request.user)
        serializer = ApiTokenSerializer(tokens, many=True)
        return Response(serializer.data)

    def create(self, request):
        scope = request.data.get("scope")
        expires_in = request.data.get("expires_in")
        client_name = request.data.get("client_name")
        device_fingerprint = request.data.get("device_fingerprint")
        if scope == "admin" and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        expires_delta = timedelta(days=int(expires_in)) if expires_in else None

        raw_token = generate_token(
            request.user,
            client_name,
            scope,
            expires_delta,
            device_fingerprint,
        )
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        api_token = ApiToken.objects.get(token_hash=token_hash)
        ApiTokenLog.objects.create(
            token=api_token,
            usuario=request.user,
            acao=ApiTokenLog.Acao.GERACAO,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        data = ApiTokenSerializer(api_token).data
        data["token"] = raw_token
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk: str | None = None):
        token = get_object_or_404(ApiToken, pk=pk)
        if not request.user.is_superuser and token.user != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        revoke_token(token.id, request.user, ip=ip, user_agent=ua)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def rotate(self, request, pk: str | None = None):
        token = get_object_or_404(ApiToken, pk=pk)
        if not request.user.is_superuser and token.user != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)

        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        raw_token = rotate_token(token.id, request.user, ip=ip, user_agent=ua)
        new_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        novo_token = ApiToken.objects.get(token_hash=new_hash)
        ApiTokenLog.objects.create(
            token=novo_token,
            usuario=request.user,
            acao=ApiTokenLog.Acao.GERACAO,
            ip=ip,
            user_agent=ua,
        )
        data = ApiTokenSerializer(novo_token).data
        data["token"] = raw_token
        return Response(data, status=status.HTTP_201_CREATED)


class ApiTokenIpViewSet(viewsets.ModelViewSet):
    queryset = ApiTokenIp.objects.all()
    serializer_class = ApiTokenIpSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        token_id = self.request.query_params.get("token")
        if token_id:
            qs = qs.filter(token_id=token_id)
        if self.request.user.is_superuser:
            return qs
        return qs.filter(token__user=self.request.user)

    def perform_create(self, serializer):
        token = serializer.validated_data["token"]
        if not self.request.user.is_superuser and token.user != self.request.user:
            raise NotFound()
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_superuser and instance.token.user != request.user:
            raise NotFound()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
