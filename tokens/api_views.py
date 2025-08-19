from __future__ import annotations

import hashlib
from datetime import timedelta

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ApiToken
from .serializers import ApiTokenSerializer
from .services import generate_token, list_tokens, revoke_token
from .metrics import (
    tokens_api_latency_seconds,
    tokens_invites_created_total,
    tokens_invites_revoked_total,
)


class ApiTokenViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        with tokens_api_latency_seconds.time():
            tokens = list_tokens(request.user)
            serializer = ApiTokenSerializer(tokens, many=True)
            return Response(serializer.data)

    def create(self, request):
        scope = request.data.get("scope")
        expires_in = request.data.get("expires_in")
        client_name = request.data.get("client_name")
        if scope == "admin" and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        expires_delta = timedelta(days=int(expires_in)) if expires_in else None
        with tokens_api_latency_seconds.time():
            raw_token = generate_token(request.user, client_name, scope, expires_delta)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            api_token = ApiToken.objects.get(token_hash=token_hash)
            data = ApiTokenSerializer(api_token).data
            data["token"] = raw_token
            tokens_invites_created_total.inc()
            return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk: str | None = None):
        token = get_object_or_404(ApiToken, pk=pk)
        if not request.user.is_superuser and token.user != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        with tokens_api_latency_seconds.time():
            revoke_token(token.id)
            tokens_invites_revoked_total.inc()
            return Response(status=status.HTTP_204_NO_CONTENT)
