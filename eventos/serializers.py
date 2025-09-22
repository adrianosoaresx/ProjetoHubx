from __future__ import annotations

import os

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from validate_docbr import CNPJ
from typing import Any, Dict
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from .validators import validate_uploaded_file

from .models import (
    BriefingEvento,
    Evento,
    EventoLog,
    InscricaoEvento,
    ParceriaEvento,
    Tarefa,
    TarefaLog,
)


class TarefaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarefa
        exclude = ("deleted", "deleted_at")
        read_only_fields = (
            "id",
            "organizacao",
            "responsavel",
            "status",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["organizacao"] = request.user.organizacao
        validated_data["responsavel"] = request.user
        instance = super().create(validated_data)
        TarefaLog.objects.create(tarefa=instance, usuario=request.user, acao="tarefa_criada")
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
        extra_kwargs = {
            "avatar": {"required": False, "allow_null": True},
            "cover": {"required": False, "allow_null": True},
        }

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

    def validate_comprovante_pagamento(self, arquivo):
        if not arquivo:
            return arquivo
        try:
            validate_uploaded_file(arquivo)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return arquivo

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

    def validate_acordo(self, arquivo):
        if not arquivo:
            return arquivo
        try:
            validate_uploaded_file(arquivo)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return arquivo

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
        message = "Já existe briefing ativo para este evento."
        if BriefingEvento.objects.filter(evento_id=evento.pk, deleted=False).exists():
            raise serializers.ValidationError({"evento": [message]})
        try:
            with transaction.atomic():
                instance = super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError({"evento": [message]}) from exc
        return instance

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
