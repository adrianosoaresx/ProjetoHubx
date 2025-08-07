from __future__ import annotations

from tempfile import NamedTemporaryFile
from typing import Iterable, Sequence


def exportar_para_arquivo(formato: str, cabecalhos: Sequence[str], linhas: Iterable[Sequence[object]]) -> str:
    """Gera arquivo temporário no formato desejado e retorna o caminho."""
    tmp = NamedTemporaryFile(delete=False, suffix=f".{formato}")
    if formato == "csv":
        import csv

        with open(tmp.name, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(list(cabecalhos))
            for linha in linhas:
                writer.writerow(list(linha))
    elif formato == "xlsx":
        try:
            from openpyxl import Workbook  # type: ignore
        except Exception as exc:  # pragma: no cover - dependência opcional
            tmp.close()
            raise RuntimeError("openpyxl não disponível") from exc
        wb = Workbook()
        ws = wb.active
        ws.append(list(cabecalhos))
        for linha in linhas:
            ws.append(list(linha))
        wb.save(tmp.name)
    else:
        tmp.close()
        raise ValueError("Formato inválido")
    tmp.close()
    return tmp.name
