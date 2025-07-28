from __future__ import annotations

from pathlib import Path

from celery import shared_task

from ..services.importacao import ImportadorPagamentos


@shared_task
def importar_pagamentos_async(file_path: str, user_id: str) -> None:
    service = ImportadorPagamentos(file_path)
    errors = service.process()
    log_path = Path(file_path).with_suffix(".log")
    if errors:
        log_path.write_text("\n".join(errors), encoding="utf-8")
    else:
        log_path.write_text("ok", encoding="utf-8")
