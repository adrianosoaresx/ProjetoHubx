from __future__ import annotations
from dataclasses import dataclass
from typing import List

from django.urls import reverse


@dataclass
class MenuItem:
    id: str
    path: str
    label: str
    icon: str
    permissions: List[str] | None = None
    classes: str = "flex items-center gap-x-2 hover:text-primary transition"


# Icons as raw HTML so they can be injected into the template safely
ICON_USER = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-6 h-6\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2\" />
  <circle cx=\"12\" cy=\"7\" r=\"4\" />
</svg>
"""

ICON_DASHBOARD = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <rect width=\"7\" height=\"9\" x=\"3\" y=\"3\" rx=\"1\" />
  <rect width=\"7\" height=\"5\" x=\"14\" y=\"3\" rx=\"1\" />
  <rect width=\"7\" height=\"9\" x=\"14\" y=\"12\" rx=\"1\" />
  <rect width=\"7\" height=\"5\" x=\"3\" y=\"16\" rx=\"1\" />
</svg>
"""

ICON_USERS = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2\" />
  <path d=\"M16 3.128a4 4 0 0 1 0 7.744\" />
  <path d=\"M22 21v-2a4 4 0 0 0-3-3.87\" />
  <circle cx=\"9\" cy=\"7\" r=\"4\" />
</svg>
"""

ICON_COMPANIES = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z\" />
  <path d=\"M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2\" />
  <path d=\"M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2\" />
  <path d=\"M10 6h4\" />
  <path d=\"M10 10h4\" />
  <path d=\"M10 14h4\" />
  <path d=\"M10 18h4\" />
</svg>
"""

ICON_EVENTOS = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M8 2v4\" />
  <path d=\"M16 2v4\" />
  <rect width=\"18\" height=\"18\" x=\"3\" y=\"4\" rx=\"2\" />
  <path d=\"M3 10h18\" />
  <path d=\"M8 14h.01\" />
  <path d=\"M12 14h.01\" />
  <path d=\"M16 14h.01\" />
  <path d=\"M8 18h.01\" />
  <path d=\"M12 18h.01\" />
  <path d=\"M16 18h.01\" />
</svg>
"""

ICON_FEED = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M4 11a9 9 0 0 1 9 9\" />
  <path d=\"M4 4a16 16 0 0 1 16 16\" />
  <circle cx=\"5\" cy=\"19\" r=\"1\" />
</svg>
"""

ICON_FINANCEIRO = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M11 15h2a2 2 0 1 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 17\" />
  <path d=\"m7 21 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9\" />
  <path d=\"m2 16 6 6\" />
  <circle cx=\"16\" cy=\"9\" r=\"2.9\" />
  <circle cx=\"6\" cy=\"5\" r=\"3\" />
</svg>
"""

ICON_ORGS = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <rect x=\"16\" y=\"16\" width=\"6\" height=\"6\" rx=\"1\" />
  <rect x=\"2\" y=\"16\" width=\"6\" height=\"6\" rx=\"1\" />
  <rect x=\"9\" y=\"2\" width=\"6\" height=\"6\" rx=\"1\" />
  <path d=\"M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3\" />
  <path d=\"M12 12V8\" />
</svg>
"""

ICON_TOKEN = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4\" />
  <path d=\"m21 2-9.6 9.6\" />
  <circle cx=\"7.5\" cy=\"15.5\" r=\"5.5\" />
</svg>
"""

ICON_CONFIG = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915\" />
  <circle cx=\"12\" cy=\"12\" r=\"3\" />
</svg>
"""

ICON_LOGOUT = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"m16 17 5-5-5-5\" />
  <path d=\"M21 12H9\" />
  <path d=\"M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4\" />
</svg>
"""

ICON_LOGIN = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"m10 17 5-5-5-5\" />
  <path d=\"M15 12H3\" />
  <path d=\"M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4\" />
</svg>
"""

ICON_REGISTER = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-5 h-5\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2\" />
  <circle cx=\"9\" cy=\"7\" r=\"4\" />
  <line x1=\"19\" x2=\"19\" y1=\"8\" y2=\"14\" />
  <line x1=\"22\" x2=\"16\" y1=\"11\" y2=\"11\" />
</svg>
"""


def build_menu(request) -> List[MenuItem]:
    """Retorna itens de menu filtrados por tipo de usuário."""
    items = [
        MenuItem(
            id="perfil",
            path=reverse("accounts:perfil"),
            label="Perfil",
            icon=ICON_USER,
            permissions=["authenticated"],
            classes="flex items-center hover:text-primary transition",
        ),
        MenuItem("dashboard", "/", "Dashboard", ICON_DASHBOARD, None),
        MenuItem("associados", reverse("associados_lista"), "Associados", ICON_USERS, ["admin", "coordenador"]),
        MenuItem("empresas", reverse("empresas:lista"), "Empresas", ICON_COMPANIES, [
            "admin",
            "financeiro",
            "coordenador",
            "nucleado",
            "associado",
            "convidado",
        ]),
        MenuItem("nucleos", reverse("nucleos:list"), "Núcleos", ICON_USERS, [
            "admin",
            "financeiro",
            "coordenador",
            "nucleado",
            "associado",
            "convidado",
        ]),
        MenuItem("meus_nucleos", reverse("nucleos:meus"), "Meus Núcleos", ICON_USERS, [
            "financeiro",
            "coordenador",
            "nucleado",
            "associado",
            "convidado",
        ]),
        MenuItem("eventos", reverse("eventos:lista"), "Eventos", ICON_EVENTOS, [
            "admin",
            "financeiro",
            "coordenador",
            "nucleado",
            "associado",
            "convidado",
        ]),
        MenuItem("feed", reverse("feed:listar"), "Feed", ICON_FEED, [
            "admin",
            "financeiro",
            "coordenador",
            "nucleado",
            "associado",
            "convidado",
        ]),
        MenuItem("financeiro", reverse("financeiro:repasses"), "Financeiro", ICON_FINANCEIRO, ["admin", "financeiro"]),
        MenuItem("organizacoes", reverse("organizacoes:list"), "Organizações", ICON_ORGS, ["root"]),
        MenuItem("token_admin", reverse("tokens:listar_api_tokens"), "Token", ICON_TOKEN, ["root", "admin"]),
        MenuItem("token_convite", reverse("tokens:gerar_convite"), "Token", ICON_TOKEN, ["coordenador"]),
        MenuItem("configuracoes", reverse("configuracoes"), "Configurações", ICON_CONFIG, ["authenticated"], "hover:text-primary transition"),
        MenuItem("logout", reverse("accounts:logout"), "Sair", ICON_LOGOUT, ["authenticated"]),
        MenuItem("login", reverse("accounts:login"), "Entrar", ICON_LOGIN, ["anonymous"]),
        MenuItem(
            "onboarding",
            reverse("accounts:onboarding"),
            "Cadastrar",
            ICON_REGISTER,
            ["anonymous"],
            classes="gap-x-2 btn btn-primary",
        ),
    ]

    user = request.user
    filtered: List[MenuItem] = []
    for item in items:
        perms = item.permissions or []
        if "anonymous" in perms and not user.is_authenticated:
            filtered.append(item)
        elif "authenticated" in perms and user.is_authenticated:
            filtered.append(item)
        elif user.is_authenticated and user.user_type in perms:
            filtered.append(item)
        elif not perms:
            filtered.append(item)
    return filtered
