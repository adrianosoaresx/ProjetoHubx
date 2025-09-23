"""Verifica divergências entre saldos de carteiras e lançamentos pagos."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.db.models.functions import Coalesce

from ...models import Carteira, LancamentoFinanceiro

ZERO = Decimal("0")
CENT = Decimal("0.01")


@dataclass(slots=True)
class ResultadoCarteira:
    """Representa o resultado consolidado de uma carteira."""

    id: str
    nome: str
    tipo_codigo: str
    tipo_rotulo: str
    centro_custo_id: str
    conta_associado_id: str
    saldo_registrado: Decimal
    saldo_calculado: Decimal
    diferenca: Decimal

    @property
    def status(self) -> str:
        return "OK" if self.diferenca == ZERO else "DIVERGENTE"


class Command(BaseCommand):
    help = (
        "Compara o saldo materializado das carteiras com o valor consolidado "
        "dos lançamentos pagos, destacando divergências."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--csv",
            dest="csv_path",
            help="Caminho opcional para exportar os resultados em CSV.",
        )

    def handle(self, *args, **options):  # type: ignore[override]
        csv_path: str | None = options.get("csv_path")

        resultados = list(self._calcular_resultados())
        self._imprimir_tabela(resultados)

        if csv_path:
            self._exportar_csv(resultados, csv_path)

        divergentes = [item for item in resultados if item.status != "OK"]
        self.stdout.write("")
        self.stdout.write(f"Carteiras analisadas: {len(resultados)}")
        if divergentes:
            self.stderr.write(
                f"Divergências encontradas em {len(divergentes)} carteiras."
            )
            raise CommandError("Saldos divergentes detectados.")
        self.stdout.write("Nenhuma divergência encontrada.")

    def _calcular_resultados(self) -> Iterable[ResultadoCarteira]:
        saldos_pagamentos = self._agrupar_lancamentos()
        carteiras = (
            Carteira.objects.select_related("centro_custo", "conta_associado")
            .order_by("nome", "id")
            .all()
        )
        for carteira in carteiras:
            saldo_registrado = self._quantizar(carteira.saldo)
            saldo_calculado = self._quantizar(saldos_pagamentos.get(carteira.id, ZERO))
            diferenca = self._quantizar(saldo_registrado - saldo_calculado)
            yield ResultadoCarteira(
                id=str(carteira.id),
                nome=carteira.nome,
                tipo_codigo=carteira.tipo,
                tipo_rotulo=carteira.get_tipo_display(),
                centro_custo_id=str(carteira.centro_custo_id or ""),
                conta_associado_id=str(carteira.conta_associado_id or ""),
                saldo_registrado=saldo_registrado,
                saldo_calculado=saldo_calculado,
                diferenca=diferenca,
            )

    def _agrupar_lancamentos(self) -> dict[UUID, Decimal]:
        pagos = LancamentoFinanceiro.objects.filter(
            status=LancamentoFinanceiro.Status.PAGO
        )
        totais: defaultdict[UUID, Decimal] = defaultdict(Decimal)
        principais = (
            pagos.values_list("carteira_id")
            .annotate(total=Coalesce(Sum("valor"), ZERO))
            .filter(carteira_id__isnull=False)
            .order_by()
        )
        for carteira_id, total in principais:
            totais[carteira_id] += total
        contrapartes = (
            pagos.values_list("carteira_contraparte_id")
            .annotate(total=Coalesce(Sum("valor"), ZERO))
            .filter(carteira_contraparte_id__isnull=False)
            .order_by()
        )
        for carteira_id, total in contrapartes:
            totais[carteira_id] += total
        return dict(totais)

    def _imprimir_tabela(self, resultados: list[ResultadoCarteira]) -> None:
        if not resultados:
            self.stdout.write("Nenhuma carteira encontrada.")
            return

        id_width = max(len("Carteira"), max(len(r.id) for r in resultados))
        nome_width = max(len("Nome"), max(len(r.nome) for r in resultados))
        tipo_width = max(len("Tipo"), max(len(r.tipo_rotulo) for r in resultados))
        valor_width = max(
            len("Registrado"),
            *(len(self._formata_decimal(r.saldo_registrado)) for r in resultados),
        )
        calculado_width = max(
            len("Calculado"),
            *(len(self._formata_decimal(r.saldo_calculado)) for r in resultados),
        )
        diff_width = max(
            len("Diferença"),
            *(len(self._formata_decimal(r.diferenca)) for r in resultados),
        )
        header = (
            f"{'Carteira':<{id_width}}  "
            f"{'Nome':<{nome_width}}  "
            f"{'Tipo':<{tipo_width}}  "
            f"{'Registrado':>{valor_width}}  "
            f"{'Calculado':>{calculado_width}}  "
            f"{'Diferença':>{diff_width}}  Status"
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for item in resultados:
            linha = (
                f"{item.id:<{id_width}}  "
                f"{item.nome:<{nome_width}}  "
                f"{item.tipo_rotulo:<{tipo_width}}  "
                f"{self._formata_decimal(item.saldo_registrado):>{valor_width}}  "
                f"{self._formata_decimal(item.saldo_calculado):>{calculado_width}}  "
                f"{self._formata_decimal(item.diferenca):>{diff_width}}  "
                f"{item.status}"
            )
            self.stdout.write(linha)

    def _exportar_csv(
        self, resultados: Iterable[ResultadoCarteira], caminho: str
    ) -> None:
        destino = Path(caminho).expanduser()
        if destino.parent and not destino.parent.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "id",
                    "nome",
                    "tipo",
                    "tipo_rotulo",
                    "centro_custo_id",
                    "conta_associado_id",
                    "saldo_registrado",
                    "saldo_calculado",
                    "diferenca",
                    "status",
                ]
            )
            for item in resultados:
                writer.writerow(
                    [
                        item.id,
                        item.nome,
                        item.tipo_codigo,
                        item.tipo_rotulo,
                        item.centro_custo_id,
                        item.conta_associado_id,
                        self._formata_decimal(item.saldo_registrado),
                        self._formata_decimal(item.saldo_calculado),
                        self._formata_decimal(item.diferenca),
                        item.status,
                    ]
                )

    @staticmethod
    def _quantizar(valor: Decimal) -> Decimal:
        return valor.quantize(CENT, rounding=ROUND_HALF_UP)

    @staticmethod
    def _formata_decimal(valor: Decimal) -> str:
        return format(valor, ".2f")
