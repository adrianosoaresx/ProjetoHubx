import json
import os
from typing import List, Dict
import requests

# Base URLs for API Tool and PDF service
API_BASE = "http://localhost:8674"
CONNECTOR_NAME = "/connector_76869538009648d5b282a4bb21c3d157"
PDF_BASE = "http://localhost:8451"


def call_api(name: str, params: Dict) -> Dict:
    """Call the given API name with the specified parameters."""
    url = f"{API_BASE}/call_api?name={name}&params={json.dumps(params)}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("result", {})


def search_repository(query: str, topn: int = 50) -> List[Dict]:
    """Search for files containing a given query in the repository."""
    params = {"query": query, "topn": topn, "repository_name": "adrianosoaresx/ProjetoHubx"}
    result = call_api(f"{CONNECTOR_NAME}/search", params)
    return result.get("results", [])


def fetch_file(url: str) -> str:
    """Fetch the content of a file from GitHub via the connector."""
    result = call_api(f"{CONNECTOR_NAME}/fetch", {"url": url})
    return result.get("content", "")


def parse_pdf(file_path: str) -> str:
    """Retrieve text from a PDF file using the PDF service."""
    pdf_url = f"{PDF_BASE}/file://{file_path}"
    resp = requests.get(pdf_url)
    resp.raise_for_status()
    return resp.text


def audit_patterns(patterns: List[str]) -> None:
    """Search for a list of patterns and print where they appear."""
    for pattern in patterns:
        print(f"\nSearching for pattern: {pattern}")
        results = search_repository(pattern, topn=20)
        if not results:
            print("  No occurrences found.")
            continue
        for idx, res in enumerate(results, 1):
            print(f"  {idx}. {res['path']}: {res['url']}")


def main():
    # Define patterns to search for legacy code
    legacy_patterns = [
        "UserType.objects",
        "TipoUsuario",
        "tipo_id",
        "data_hora",
        "duracao",
        "link_inscricao",
        "inscritos",
        "Mensagem(",
        "Notificacao(",
        "Topico(",
        "Resposta(",
        "Post.PUBLICO",
    ]
    audit_patterns(legacy_patterns)

    # Example: parse a PDF to view requirements (adjust paths as needed)
    # pdf_text = parse_pdf("/home/oai/share/Requisitos_Accounts_Hubx.pdf")
    # print(pdf_text[:500])


if __name__ == "__main__":
    main()
