from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from dateutil.parser import parse
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from ..serializers import LancamentoFinanceiroSerializer


@dataclass
class ImportResult:
    """Resultado da importação de pagamentos."""

    preview: list[dict[str, Any]]
    errors: list[str]


class ImportadorPagamentos:
    """Serviço para importar pagamentos a partir de arquivos CSV ou XLSX."""

    REQUIRED = {
        "centro_custo_id",
        "conta_associado_id",
        "tipo",
        "valor",
        "data_lancamento",
        "status",
    }

    def __init__(self, file_path: str, preview_limit: int = 5) -> None:
        self.file_path = Path(file_path)
        self.preview_limit = preview_limit

    # ────────────────────────────────────────────────────────────
    def _iter_rows(self) -> Iterable[dict[str, str]]:
        """Itera sobre as linhas do arquivo e gera dicionários de dados."""
        name = self.file_path.name.lower()
        if name.endswith(".csv"):
            with self.file_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return
                missing = self.REQUIRED - set(h.lower() for h in reader.fieldnames)
                if missing:
                    raise ValueError(_(f"Colunas faltantes: {', '.join(missing)}"))
                for row in reader:
                    yield {k.strip(): (v or "").strip() for k, v in row.items()}
        elif name.endswith(".xlsx"):
            try:
                from openpyxl import load_workbook
            except Exception as exc:  # pragma: no cover - openpyxl optional
                raise ValueError(_("openpyxl não disponível")) from exc
            wb = load_workbook(self.file_path, read_only=True)
            ws = wb.active
            rows = ws.iter_rows(values_only=True)
            headers = next(rows)
            if not headers:
                return
            missing = self.REQUIRED - {str(h).lower() for h in headers}
            if missing:
                raise ValueError(_(f"Colunas faltantes: {', '.join(missing)}"))
            for values in rows:
                row = {str(h).strip(): str(v).strip() if v is not None else "" for h, v in zip(headers, values)}
                yield row
        else:
            raise ValueError(_("Formato não suportado"))

    # ────────────────────────────────────────────────────────────
    def preview(self) -> ImportResult:
        """Lê o arquivo e retorna uma prévia dos lançamentos."""
        preview: list[dict[str, Any]] = []
        errors: list[str] = []
        try:
            for idx, row in enumerate(self._iter_rows(), start=2):
                try:
                    record = self._convert_row(row)
                    if len(preview) < self.preview_limit:
                        preview.append(
                            {
                                "centro_custo": str(record["centro_custo"].id),
                                "conta_associado": (
                                    str(record["conta_associado"].id) if record.get("conta_associado") else None
                                ),
                                "tipo": record["tipo"],
                                "valor": str(record["valor"]),
                                "data_lancamento": record["data_lancamento"].isoformat(),
                                "data_vencimento": record["data_vencimento"].isoformat(),
                                "status": record["status"],
                                "descricao": record["descricao"],
                            }
                        )
                except Exception as exc:
                    errors.append(f"Linha {idx}: {exc}")
        except Exception as exc:
            errors.append(str(exc))
        return ImportResult(preview=preview, errors=errors)

    # ────────────────────────────────────────────────────────────
    def process(self, batch_size: int = 500) -> list[str]:
        """Processa o arquivo criando lançamentos em lote."""
        errors: list[str] = []
        batch: list[dict[str, Any]] = []

        def flush(chunk: list[dict[str, Any]]):
            to_create = []
            saldo_centro: dict[str, Decimal] = {}
            saldo_conta: dict[str, Decimal] = {}
            for item in chunk:
                payload = {
                    "centro_custo": str(item["centro_custo"].id),
                    "conta_associado": str(item["conta_associado"].id) if item.get("conta_associado") else None,
                    "tipo": item["tipo"],
                    "valor": str(item["valor"]),
                    "data_lancamento": item["data_lancamento"].isoformat(),
                    "data_vencimento": item["data_vencimento"].isoformat(),
                    "status": item["status"],
                    "descricao": item["descricao"],
                }
                serializer = LancamentoFinanceiroSerializer(data=payload)
                if not serializer.is_valid():
                    errors.append(f"Dados inválidos na linha: {serializer.errors}")
                    continue
                data = serializer.validated_data
                if data["status"] == LancamentoFinanceiro.Status.PAGO:
                    cid = str(data["centro_custo"].id)
                    saldo_centro[cid] = saldo_centro.get(cid, Decimal("0")) + data["valor"]
                    conta = data.get("conta_associado")
                    if conta:
                        aid = str(conta.id)
                        saldo_conta[aid] = saldo_conta.get(aid, Decimal("0")) + data["valor"]
                to_create.append(LancamentoFinanceiro(**data))
            if to_create:
                LancamentoFinanceiro.objects.bulk_create(to_create)
            for cid, inc in saldo_centro.items():
                CentroCusto.objects.filter(pk=cid).update(saldo=F("saldo") + inc)
            for aid, inc in saldo_conta.items():
                ContaAssociado.objects.filter(pk=aid).update(saldo=F("saldo") + inc)

        for idx, row in enumerate(self._iter_rows(), start=2):
            try:
                batch.append(self._convert_row(row))
            except Exception as exc:
                errors.append(f"Linha {idx}: {exc}")
                continue
            if len(batch) >= batch_size:
                with transaction.atomic():
                    flush(batch)
                batch = []
        if batch:
            with transaction.atomic():
                flush(batch)
        return errors

    # ────────────────────────────────────────────────────────────
    def _convert_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Converte uma linha do arquivo em dados validados."""
        centro = CentroCusto.objects.get(pk=row["centro_custo_id"])
        conta: ContaAssociado | None = None
        cid = row.get("conta_associado_id")
        email = row.get("email")
        if cid:
            conta = ContaAssociado.objects.filter(pk=cid).first()
        elif email:
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(email=email, username=email.split("@")[0])
            conta, _ = ContaAssociado.objects.get_or_create(user=user)
        if not conta:
            raise ValueError(_("Conta do associado não encontrada"))
        data_lanc = parse(row["data_lancamento"])
        if not data_lanc.tzinfo:
            data_lanc = timezone.make_aware(data_lanc)
        data_vencimento = row.get("data_vencimento")
        if data_vencimento:
            venc = parse(data_vencimento)
            if not venc.tzinfo:
                venc = timezone.make_aware(venc)
            if venc < data_lanc:
                raise ValueError(_("data_vencimento anterior a data_lancamento"))
        else:
            venc = data_lanc
        return {
            "centro_custo": centro,
            "conta_associado": conta,
            "tipo": row["tipo"],
            "valor": Decimal(row["valor"]),
            "data_lancamento": data_lanc,
            "data_vencimento": venc,
            "status": row["status"],
            "descricao": row.get("descricao", ""),
        }
