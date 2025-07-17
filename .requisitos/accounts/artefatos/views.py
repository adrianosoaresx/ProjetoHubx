from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from accounts.models import User, ConfiguracaoConta, ParticipacaoNucleo
from accounts.serializers import (
    UserSerializer,
    ChangePasswordSerializer,
    ConfiguracaoContaSerializer,
    ParticipacaoNucleoSerializer,
)


@extend_schema(
    responses=UserSerializer,
    request=UserSerializer,
    description="Visualizar ou atualizar dados de perfil do usuário autenticado."
)
class PerfilUsuarioView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    request=ChangePasswordSerializer,
    responses={204: None, 400: {"type": "object", "properties": {"erro": {"type": "string"}}}},
    description="Trocar senha do usuário autenticado, com verificação da senha atual."
)
class TrocarSenhaView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        senha_atual = serializer.validated_data["senha_atual"]
        nova_senha = serializer.validated_data["nova_senha"]

        if not check_password(senha_atual, user.password):
            return Response({"erro": "Senha atual incorreta."}, status=400)

        user.set_password(nova_senha)
        user.save()
        RefreshToken.for_user(user)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    responses=ConfiguracaoContaSerializer,
    request=ConfiguracaoContaSerializer,
    description="Recupera ou atualiza as preferências de notificações e tema do usuário."
)
class PreferenciasView(generics.RetrieveUpdateAPIView):
    serializer_class = ConfiguracaoContaSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.configuracoes


@extend_schema(
    responses=ParticipacaoNucleoSerializer(many=True),
    description="Lista os núcleos onde o usuário está vinculado, com ou sem coordenação."
)
class ParticipacoesView(generics.ListAPIView):
    serializer_class = ParticipacaoNucleoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ParticipacaoNucleo.objects.filter(user=self.request.user)
