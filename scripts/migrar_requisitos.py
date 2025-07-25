#!/usr/bin/env python3
# scripts/migrar_requisitos.py
"""
Migra arquivos PDF de requisitos presentes em .requisitos/ (na raiz) para Markdown
padronizado em subpastas `.requisitos/<app>/`, mantendo os PDFs originais.

Uso:
    python scripts/migrar_requisitos.py

Dependências:
    pip install pdfplumber python-slugify pyyaml rich
"""

from __future__ import annotations

import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

import pdfplumber
import yaml
from rich.console import Console
from rich.logging import RichHandler
from slugify import slugify

# --------------------------------------------------------------------------- #
# Logging                                                                    #
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)
logger = logging.getLogger(__name__)
console = Console()

# --------------------------------------------------------------------------- #
# Constantes                                                                  #
# --------------------------------------------------------------------------- #
ROOT_DIR = Path.cwd()
REQ_DIR = ROOT_DIR / ".requisitos"
PDF_PATTERN = "*.pdf"
MODULE_REGEX = re.compile(r"requisitos_(.+?)_hubx", flags=re.IGNORECASE)
ID_TEMPLATE = "REQ-{module}-{seq:03d}"
YAML_DELIM = "---"
INDEX_FILE = REQ_DIR / "_index.md"


# --------------------------------------------------------------------------- #
# Funções utilitárias                                                         #
# --------------------------------------------------------------------------- #
def discover_pdfs() -> List[Path]:
    """
    Lista todos os PDFs diretamente em .requisitos/ (não entra em subpastas).
    """
    pdfs = sorted(REQ_DIR.glob(PDF_PATTERN))
    logger.info("📄 %d PDFs encontrados em %s", len(pdfs), REQ_DIR)
    for p in pdfs:
        logger.debug("  – %s", p)
    return pdfs


def extract_module(file_name: str) -> str:
    """
    Deriva o nome do app/módulo a partir do nome do PDF.
    Ex.: Requisitos_Eventos_Hubx.pdf → eventos
    """
    match = MODULE_REGEX.search(file_name)
    raw = match.group(1) if match else Path(file_name).stem
    return slugify(raw, separator="_").lower()


def next_sequence(module_dir: Path, module: str) -> int:
    """
    Calcula o próximo NNN para arquivos existentes em module_dir.
    """
    seqs: List[int] = []
    pattern = re.compile(rf"REQ-{module.upper()}-(\d{{3}})\.md$")
    for f in module_dir.glob("REQ-*-*.md"):
        m = pattern.match(f.name)
        if m:
            seqs.append(int(m.group(1)))
    return max(seqs, default=0) + 1


def pdf_to_text(pdf_path: Path) -> str:
    """
    Extrai texto de todas as páginas do PDF.
    """
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n\n".join(pages).strip()


def build_markdown(
    *,
    req_id: str,
    title: str,
    module: str,
    source: str,
    imported_text: str,
) -> str:
    """
    Gera o Markdown completo a partir do template.
    """
    today = date.today().isoformat()
    front = {
        "id": req_id,
        "title": title,
        "module": module.capitalize(),
        "status": "Em vigor",
        "version": "1.0",
        "authors": [],
        "created": today,
        "updated": today,
        "source": source,
    }
    yaml_block = yaml.dump(front, allow_unicode=True, sort_keys=False).rstrip()
    return (
        f"{YAML_DELIM}\n{yaml_block}\n{YAML_DELIM}\n\n"
        "## 1. Visão Geral\n\n<descrição curta>\n\n"
        "## 2. Escopo\n"
        "- **Inclui**:\n"
        "- **Exclui**:\n\n"
        "## 3. Requisitos Funcionais\n"
        "| Código | Descrição | Prioridade | Critérios de Aceite |\n"
        "|--------|-----------|-----------|---------------------|\n\n"
        "## 4. Requisitos Não-Funcionais\n"
        "| Código | Categoria | Descrição | Métrica/Meta |\n"
        "|--------|-----------|-----------|--------------|\n\n"
        "## 5. Fluxo de Usuário / Caso de Uso\n"
        "```mermaid\nflowchart TD\n    U[Usuário] -->|Interação| S[Sistema]\n```\n\n"
        "### UC-01 – Descrição\n\n"
        "## 6. Regras de Negócio\n\n"
        "## 7. Modelo de Dados\n\n"
        "## 8. Critérios de Aceite (Gherkin)\n"
        "```gherkin\nFeature: <nome>\n```\n\n"
        "## 9. Dependências / Integrações\n\n"
        "## 10. Anexos e Referências\n"
        f"- Documento fonte: {source}\n\n"
        "## 99. Conteúdo Importado (para revisão)\n\n"
        "```\n"
        f"{imported_text}\n"
        "```\n"
    )


def update_index() -> None:
    """
    Atualiza .requisitos/_index.md com todos os requisitos migrados.
    """
    rows: List[str] = []
    for md in REQ_DIR.rglob("REQ-*-*.md"):
        with md.open(encoding="utf-8") as f:
            if f.readline().strip() != YAML_DELIM:
                continue
            yaml_lines: List[str] = []
            for line in f:
                if line.strip() == YAML_DELIM:
                    break
                yaml_lines.append(line)
            data = yaml.safe_load("".join(yaml_lines))
            rows.append(
                "| {id} | {title} | {module} | {status} | {version} | {updated} |".format(
                    **data
                )
            )
    header = (
        "# Índice de Requisitos\n\n"
        "| ID | Título | Módulo | Status | Versão | Última atualização |\n"
        "|----|--------|--------|--------|--------|--------------------|\n"
    )
    INDEX_FILE.write_text(header + "\n".join(sorted(rows)), encoding="utf-8")
    logger.info("📑 Índice atualizado com %d itens", len(rows))


def process_pdf(pdf_path: Path) -> Optional[Path]:
    """
    Converte um PDF em Markdown, sem mover ou excluir o PDF.
    """
    module = extract_module(pdf_path.name)
    module_dir = REQ_DIR / module
    module_dir.mkdir(parents=True, exist_ok=True)

    seq = next_sequence(module_dir, module)
    req_id = ID_TEMPLATE.format(module=module.upper(), seq=seq)
    md_path = module_dir / f"{req_id}.md"

    if md_path.exists():
        logger.info("⏭️  %s já existe – pulando", md_path)
        return None

    try:
        text = pdf_to_text(pdf_path)
    except Exception as e:
        logger.error("❌ Falha ao ler %s: %s", pdf_path, e)
        return None

    title = pdf_path.stem.replace("_", " ").title()
    md = build_markdown(
        req_id=req_id,
        title=title,
        module=module,
        source=pdf_path.name,
        imported_text=text,
    )
    md_path.write_text(md, encoding="utf-8")
    logger.info("✅ Criado %s", md_path)
    return md_path


def main() -> None:
    pdfs = discover_pdfs()
    if not pdfs:
        console.print(f"[bold yellow]Nenhum PDF encontrado em {REQ_DIR}[/]")
        sys.exit(0)

    created: List[Path] = []
    for pdf in pdfs:
        result = process_pdf(pdf)
        if result:
            created.append(result)

    if created:
        update_index()
        console.print(f"[bold green]🎉 {len(created)} requisito(s) migrado(s)![/]")
    else:
        console.print("[bold cyan]Nenhum novo requisito criado.[/]")

if __name__ == "__main__":
    main()
