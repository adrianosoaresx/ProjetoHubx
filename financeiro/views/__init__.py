from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CentroCusto, LancamentoFinanceiro
from ..serializers import (
    CentroCustoSerializer,
    ImportarPagamentosConfirmacaoSerializer,
    ImportarPagamentosPreviewSerializer,
    LancamentoFinanceiroSerializer,
)
from ..services.importacao import ImportadorPagamentos
from ..tasks.importar_pagamentos import importar_pagamentos_async


class CentroCustoViewSet(viewsets.ModelViewSet):
    queryset = CentroCusto.objects.all()
    serializer_class = CentroCustoSerializer
    permission_classes = [IsAuthenticated]


class FinanceiroViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="importar-pagamentos")
    def importar_pagamentos(self, request):
        serializer = ImportarPagamentosPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]
        uid = uuid.uuid4().hex
        saved = default_storage.save(f"importacoes/{uid}_{file.name}", file)
        full_path = default_storage.path(saved)
        service = ImportadorPagamentos(full_path)
        result = service.preview()
        if result.errors and not result.preview:
            return Response({"erros": result.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": uid, "preview": result.preview, "erros": result.errors}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="importar-pagamentos/confirmar")
    def confirmar_importacao(self, request):
        serializer = ImportarPagamentosConfirmacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["id"]
        # encontra arquivo salvo
        media_path = Path(settings.MEDIA_ROOT) / "importacoes"
        files = list(media_path.glob(f"{uid}_*"))
        if not files:
            return Response({"detail": "Arquivo não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        file_path = str(files[0])
        importar_pagamentos_async.delay(file_path, str(request.user.id))
        return Response({"detail": "Importação iniciada"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"], url_path="relatorios")
    def relatorios(self, request):
        centro_id = request.query_params.get("centro")
        periodo = request.query_params.get("periodo")
        inicio: datetime | None = None
        fim: datetime | None = None
        if periodo:
            dt = parse_date(f"{periodo}-01")
            if dt:
                inicio = datetime(dt.year, dt.month, 1)
                if dt.month == 12:
                    fim = datetime(dt.year + 1, 1, 1)
                else:
                    fim = datetime(dt.year, dt.month + 1, 1)
        lancamentos = LancamentoFinanceiro.objects.all()
        if centro_id:
            lancamentos = lancamentos.filter(centro_custo_id=centro_id)
        if inicio and fim:
            lancamentos = lancamentos.filter(data_lancamento__gte=inicio, data_lancamento__lt=fim)
        receitas = lancamentos.filter(valor__gt=0).aggregate(total=Sum("valor"))["total"] or 0
        despesas = lancamentos.filter(valor__lt=0).aggregate(total=Sum("valor"))["total"] or 0
        saldo = receitas + despesas
        return Response({"saldo": saldo, "receitas": receitas, "despesas": abs(despesas)})

    @action(detail=False, methods=["get"], url_path="inadimplencias")
    def inadimplencias(self, request):
        pendentes = LancamentoFinanceiro.objects.filter(status=LancamentoFinanceiro.Status.PENDENTE)
        serializer = LancamentoFinanceiroSerializer(pendentes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="aportes")
    def aportes(self, request):
        data = request.data.copy()
        if "tipo" not in data:
            data["tipo"] = LancamentoFinanceiro.Tipo.APORTE_INTERNO
        serializer = LancamentoFinanceiroSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        lancamento = serializer.save()
        out = LancamentoFinanceiroSerializer(lancamento)
        return Response(out.data, status=status.HTTP_201_CREATED)
