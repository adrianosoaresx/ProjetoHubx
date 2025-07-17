from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from accounts.models import User, ConfiguracaoConta, ParticipacaoNucleo


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "nome_completo", "email", "cpf", "biografia",
            "avatar", "cover", "redes_sociais", "organizacao", "is_associado"
        ]
        read_only_fields = ["id", "is_associado", "organizacao"]


class ChangePasswordSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True)
    nova_senha = serializers.CharField(write_only=True)

    def validate_nova_senha(self, value):
        validate_password(value)
        return value


class ConfiguracaoContaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoConta
        fields = [
            "receber_notificacoes_email",
            "receber_notificacoes_whatsapp",
            "tema_escuro"
        ]


class ParticipacaoNucleoSerializer(serializers.ModelSerializer):
    nome_nucleo = serializers.CharField(source="nucleo.nome", read_only=True)

    class Meta:
        model = ParticipacaoNucleo
        fields = ["nucleo", "nome_nucleo", "is_coordenador"]
