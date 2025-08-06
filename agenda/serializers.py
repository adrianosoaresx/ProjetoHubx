from __future__ import annotations

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from validate_docbr import CNPJ
from typing import Any, Dict

from .models import (
    BriefingEvento,
    Evento,
    EventoLog,
    InscricaoEvento,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
)
from .tasks import upload_material_divulgacao


class EventoSerializer(serializers.ModelSerializer):
    nota_media = serializers.SerializerMethodField()
    distribuicao_notas = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "organizacao",
            "coordenador",
            "created",
            "modified",
            "nota_media",
            "distribuicao_notas",
        )

    def get_nota_media(self, obj: Evento):
        notas = obj.inscricoes.filter(avaliacao__isnull=False).values_list("avaliacao", flat=True)
        if not notas:
            return None
        return round(sum(notas) / len(notas), 2)

    def get_distribuicao_notas(self, obj: Evento):
        dist = {str(i): 0 for i in range(1, 6)}
        for nota in obj.inscricoes.filter(avaliacao__isnull=False).values_list("avaliacao", flat=True):
            dist[str(nota)] += 1
        return dist

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["organizacao"] = request.user.organizacao
        validated_data["coordenador"] = request.user
        instance = super().create(validated_data)
        EventoLog.objects.create(evento=instance, usuario=request.user, acao="evento_criado")
        return instance

    def update(self, instance, validated_data):
        request = self.context["request"]
        old_instance = Evento.objects.get(pk=instance.pk)
        instance = super().update(instance, validated_data)
        changes: Dict[str, Dict[str, Any]] = {}
        for field in validated_data:
            before = getattr(old_instance, field)
            after = getattr(instance, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        EventoLog.objects.create(
            evento=instance,
            usuario=request.user,
            acao="evento_atualizado",
            detalhes=changes,
        )
        return instance


class InscricaoEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InscricaoEvento
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "user",
            "status",
            "data_confirmacao",
            "qrcode_url",
            "check_in_realizado_em",
            "posicao_espera",
            "avaliacao",
            "feedback",
            "created",
            "modified",
        )

    def create(self, validated_data):
        request = self.context["request"]
        evento = validated_data["evento"]
        if evento.organizacao != request.user.organizacao:
            raise PermissionDenied("Evento de outra organização")
        if InscricaoEvento.objects.filter(user=request.user, evento=evento, deleted=False).exists():
            raise serializers.ValidationError("Usuário já inscrito neste evento.")
        validated_data["user"] = request.user
        instance = super().create(validated_data)
        instance.confirmar_inscricao()
        return instance


class MaterialDivulgacaoEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialDivulgacaoEvento
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "status",
            "avaliado_por",
            "avaliado_em",
            "imagem_thumb",
            "created",
            "modified",
        )

    def create(self, validated_data):
        request = self.context["request"]
        evento = validated_data["evento"]
        if evento.organizacao != request.user.organizacao:
            raise PermissionDenied("Evento de outra organização")
        instance = super().create(validated_data)
        upload_material_divulgacao.delay(instance.pk)
        return instance

    def update(self, instance, validated_data):
        request = self.context["request"]
        old_instance = MaterialDivulgacaoEvento.objects.get(pk=instance.pk)
        instance = super().update(instance, validated_data)
        if "arquivo" in validated_data:
            upload_material_divulgacao.delay(instance.pk)
        changes: Dict[str, Dict[str, Any]] = {}
        for field in validated_data:
            before = getattr(old_instance, field)
            after = getattr(instance, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=request.user,
            acao="material_atualizado",
            detalhes=changes,
        )
        return instance


class ParceriaEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParceriaEvento
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "avaliacao",
            "comentario",
            "created",
            "modified",
        )

    def validate_cnpj(self, value: str) -> str:
        if not CNPJ().validate(value):
            raise serializers.ValidationError("CNPJ inválido")
        return value

    def validate(self, attrs):
        if attrs.get("data_fim") and attrs.get("data_inicio") and attrs["data_fim"] < attrs["data_inicio"]:
            raise serializers.ValidationError({"data_fim": "Data final deve ser posterior à inicial"})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        evento = validated_data["evento"]
        if evento.organizacao != request.user.organizacao:
            raise PermissionDenied("Evento de outra organização")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context["request"]
        old_instance = ParceriaEvento.objects.get(pk=instance.pk)
        instance = super().update(instance, validated_data)
        changes: Dict[str, Dict[str, Any]] = {}
        for field in validated_data:
            before = getattr(old_instance, field)
            after = getattr(instance, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=request.user,
            acao="parceria_atualizada",
            detalhes=changes,
        )
        return instance


class BriefingEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BriefingEvento
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "status",
            "orcamento_enviado_em",
            "aprovado_em",
            "recusado_em",
            "coordenadora_aprovou",
            "recusado_por",
            "prazo_limite_resposta",
            "avaliado_por",
            "avaliado_em",
            "created",
            "modified",
        )

    def create(self, validated_data):
        request = self.context["request"]
        evento = validated_data["evento"]
        if evento.organizacao != request.user.organizacao:
            raise PermissionDenied("Evento de outra organização")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context["request"]
        old_instance = BriefingEvento.objects.get(pk=instance.pk)
        instance = super().update(instance, validated_data)
        changes: Dict[str, Dict[str, Any]] = {}
        for field in validated_data:
            before = getattr(old_instance, field)
            after = getattr(instance, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        EventoLog.objects.create(
            evento=instance.evento,
            usuario=request.user,
            acao="briefing_atualizado",
            detalhes=changes,
        )
        return instance
