from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import AccountToken, User, UserRating


class UserSerializer(serializers.ModelSerializer):
    tipo_usuario = serializers.CharField(source="get_tipo_usuario", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "is_associado",
            "is_coordenador",
            "nucleo_id",
            "organizacao_id",
            "tipo_usuario",
            "deleted",
            "deleted_at",
            "two_factor_enabled",
        ]


class AccountTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountToken
        fields = [
            "codigo",
            "tipo",
            "usuario",
            "expires_at",
            "used_at",
            "status",
        ]
        read_only_fields = ["codigo", "usuario", "used_at", "status"]


class UserRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRating
        fields = ["id", "rated_user", "rated_by", "score", "comment", "created_at"]
        read_only_fields = ["rated_user", "rated_by", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        rated_user = self.context.get("rated_user") or attrs.get("rated_user")

        if not user or not user.is_authenticated:
            raise serializers.ValidationError(_("Autenticação obrigatória."))

        if not user.has_perm("accounts.add_userrating"):
            raise serializers.ValidationError(_("Você não tem permissão para avaliar usuários."))

        if rated_user and rated_user == user:
            raise serializers.ValidationError(_("Você não pode avaliar seu próprio perfil."))

        if rated_user and UserRating.objects.filter(rated_by=user, rated_user=rated_user).exists():
            raise serializers.ValidationError(_("Você já avaliou este usuário."))

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        rated_user = self.context.get("rated_user")
        rating = UserRating(
            rated_by=user,
            rated_user=rated_user,
            score=validated_data["score"],
            comment=validated_data.get("comment", ""),
        )
        rating.full_clean_with_user(user)
        rating.save()
        return rating
