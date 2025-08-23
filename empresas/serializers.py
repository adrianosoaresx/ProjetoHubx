from __future__ import annotations

from rest_framework import serializers
from validate_docbr import CNPJ

from .models import AvaliacaoEmpresa, ContatoEmpresa, Empresa, EmpresaChangeLog, Tag


class TagSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Tag
        fields = ["id", "nome", "categoria", "parent"]


class EmpresaSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)
    favoritado = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "organizacao",
            "nome",
            "cnpj",
            "tipo",
            "municipio",
            "estado",
            "logo",
            "descricao",
            "palavras_chave",
            "validado_em",
            "fonte_validacao",
            "tags",
            "versao",
            "favoritado",
            "deleted",
        ]
        read_only_fields = [
            "usuario",
            "organizacao",
            "deleted",
            "versao",
            "favoritado",
            "validado_em",
            "fonte_validacao",
        ]

    def validate_cnpj(self, value: str) -> str:
        """Valida e formata o CNPJ recebido.

        Utiliza a biblioteca ``validate_docbr`` para garantir que o CNPJ é
        válido e aplica a máscara padrão. Também verifica se já existe outra
        empresa cadastrada com o mesmo CNPJ.
        """

        cnpj = CNPJ()
        digits = "".join(filter(str.isdigit, value))

        if not cnpj.validate(digits):
            raise serializers.ValidationError("CNPJ inválido")

        formatted = cnpj.mask(digits)
        qs = Empresa.objects.filter(cnpj=formatted).exclude(pk=getattr(self.instance, "pk", None))

        if qs.exists():
            raise serializers.ValidationError("CNPJ já cadastrado")

        return formatted

    def create(self, validated_data: dict) -> Empresa:
        tags = validated_data.pop("tags", [])
        empresa = Empresa.objects.create(**validated_data)
        if tags:
            empresa.tags.set(tags)
        return empresa

    def update(self, instance: Empresa, validated_data: dict) -> Empresa:
        tags = validated_data.pop("tags", None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        return instance

    def get_favoritado(self, obj: Empresa) -> bool:
        """Retorna ``True`` se a empresa estiver favoritada pelo usuário atual."""

        request = self.context.get("request")

        # Quando o serializer é utilizado fora de uma requisição (ex.: para
        # renderizar templates), o atributo ``favoritado`` pode ser definido
        # previamente no objeto. Nesse caso, apenas retornamos o valor já
        # calculado.
        if not request or not request.user.is_authenticated:
            return getattr(obj, "favoritado", False)

        # Para requisições autenticadas, verifica a existência do favorito no
        # banco caso o atributo ainda não esteja presente.
        if hasattr(obj, "favoritado"):
            return bool(obj.favoritado)

        return obj.favoritos.filter(usuario=request.user, deleted=False).exists()


class EmpresaChangeLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", default=None)

    class Meta:
        model = EmpresaChangeLog
        fields = [
            "id",
            "campo_alterado",
            "valor_antigo",
            "valor_novo",
            "created_at",
            "usuario_email",
        ]


class ContatoEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContatoEmpresa
        fields = ["id", "nome", "cargo", "email", "telefone", "principal"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        principal = attrs.get("principal", getattr(self.instance, "principal", False))
        empresa = self.context.get("empresa") or getattr(self.instance, "empresa", None)
        if principal and empresa:
            qs = ContatoEmpresa.objects.filter(empresa=empresa, principal=True, deleted=False)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"principal": "Já existe um contato principal para esta empresa."})
        return attrs


class AvaliacaoEmpresaSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = AvaliacaoEmpresa
        fields = [
            "id",
            "empresa",
            "usuario",
            "usuario_email",
            "nota",
            "comentario",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["empresa", "usuario", "created_at", "updated_at"]
