from __future__ import annotations

import os

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
    Tarefa,
    TarefaLog,
)
from .tasks import upload_material_divulgacao
from dashboard.services import check_achievements


class TarefaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarefa
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "organizacao",
            "responsavel",
            "status",
            "mensagem_origem",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["organizacao"] = request.user.organizacao
        validated_data["responsavel"] = request.user
        instance = super().create(validated_data)
        TarefaLog.objects.create(
            tarefa=instance, usuario=request.user, acao="tarefa_criada"
        )
        return instance

    def update(self, instance, validated_data):
        request = self.context["request"]
        old_instance = Tarefa.objects.get(pk=instance.pk)
        instance = super().update(instance, validated_data)
        changes: Dict[str, Dict[str, Any]] = {}
        for field in validated_data:
            before = getattr(old_instance, field)
            after = getattr(instance, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        TarefaLog.objects.create(
            tarefa=instance,
            usuario=request.user,
            acao="tarefa_atualizada",
            detalhes=changes,
        )
        return instance


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
            "created_at",
            "updated_at",
            "nota_media",
            "distribuicao_notas",
        )

    def get_nota_media(self, obj: Evento):
        media = obj.calcular_media_feedback()
        return round(media, 2) if media else None

    def get_distribuicao_notas(self, obj: Evento):
        dist = {str(i): 0 for i in range(1, 6)}
        for nota in obj.feedbacks.values_list("nota", flat=True):
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
            "created_at",
            "updated_at",
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
        check_achievements(request.user)
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
            "created_at",
            "updated_at",
        )

    def validate_arquivo(self, arquivo):
        if not arquivo:
            return arquivo
        ext = os.path.splitext(arquivo.name)[1].lower()
        if ext in {".jpg", ".jpeg", ".png"}:
            max_size = 10 * 1024 * 1024
        elif ext == ".pdf":
            max_size = 20 * 1024 * 1024
        else:
            raise serializers.ValidationError("Formato de arquivo não permitido.")
        if arquivo.size > max_size:
            raise serializers.ValidationError("Arquivo excede o tamanho máximo permitido.")
        return arquivo


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
            "created_at",
            "updated_at",
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
            "created_at",
            "updated_at",
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
