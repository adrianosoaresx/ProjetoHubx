from __future__ import annotations

from datetime import datetime

from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CentroCusto, LancamentoFinanceiro
from ..serializers import (
    CentroCustoSerializer,
    ImportarPagamentosSerializer,
    LancamentoFinanceiroSerializer,
)


class CentroCustoViewSet(viewsets.ModelViewSet):
    queryset = CentroCusto.objects.all()
    serializer_class = CentroCustoSerializer
    permission_classes = [IsAuthenticated]


class FinanceiroViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="importar-pagamentos")
    def importar_pagamentos(self, request):
        serializer = ImportarPagamentosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Validação mínima, processamento simplificado
        return Response(status=status.HTTP_201_CREATED)

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
