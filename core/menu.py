from __future__ import annotations
from dataclasses import dataclass, replace
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
    children: List["MenuItem"] | None = None


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

ICON_INFO = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <circle cx=\"12\" cy=\"12\" r=\"10\" />
  <path d=\"M12 16v-4\" />
  <path d=\"M12 8h.01\" />
</svg>
"""

ICON_BRIEFCASE = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z\" />
  <path d=\"M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2\" />
  <path d=\"M3 13h18\" />
</svg>
"""

ICON_CHAT = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z\" />
</svg>
"""

ICON_STAR = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <polygon points=\"12 17.27 18.18 21 16.54 13.97 22 9.24 14.81 8.63 12 2 9.19 8.63 2 9.24 7.46 13.97 5.82 21 12 17.27\" />
</svg>
"""

ICON_LOCK = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <rect width=\"18\" height=\"11\" x=\"3\" y=\"11\" rx=\"2\" />
  <path d=\"M7 11V7a5 5 0 0 1 10 0v4\" />
</svg>
"""

ICON_SETTINGS = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z\" />
  <path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z\" />
</svg>
"""

ICON_LINK = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M9 15 7.5 16.5a3.54 3.54 0 0 1-5-5L5 9\" />
  <path d=\"m15 9 1.5-1.5a3.54 3.54 0 0 1 5 5L19 15\" />
  <path d=\"m8 12 4 0\" />
  <path d=\"m12 12 4 0\" />
</svg>
"""

ICON_PLUS = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M12 5v14\" />
  <path d=\"M5 12h14\" />
</svg>
"""

ICON_CHART = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M3 3v18h18\" />
  <path d=\"m9 17 2-3 3 2 4-6\" />
</svg>
"""

ICON_BUILDING = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M3 21V7a2 2 0 0 1 2-2h3V3a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2h3a2 2 0 0 1 2 2v14\" />
  <path d=\"M9 21V9\" />
  <path d=\"M15 21V9\" />
  <path d=\"M3 21h18\" />
</svg>
"""

ICON_PLUG = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M10 4V2\" />
  <path d=\"M14 4V2\" />
  <path d=\"M7 8h10\" />
  <path d=\"M7 8a5 5 0 0 0 10 0\" />
  <path d=\"M12 13v9\" />
</svg>
"""

ICON_DOWNLOAD = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\" />
  <path d=\"m7 10 5 5 5-5\" />
  <path d=\"M12 15V3\" />
</svg>
"""

ICON_UPLOAD = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\" />
  <path d=\"m17 9-5-5-5 5\" />
  <path d=\"M12 4v12\" />
</svg>
"""

ICON_TABLE = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M3 10h18\" />
  <path d=\"M10 3v18\" />
  <rect width=\"18\" height=\"18\" x=\"3\" y=\"3\" rx=\"2\" />
</svg>
"""

ICON_FILE_SEARCH = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9.5Z\" />
  <path d=\"M14 2v6h6\" />
  <path d=\"M9 11h1\" />
  <path d=\"M9 15h6\" />
  <circle cx=\"11.5\" cy=\"17.5\" r=\"2.5\" />
  <path d=\"m13.3 19.3 1.4 1.4\" />
</svg>
"""

ICON_TREND_UP = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"m3 17 6-6 4 4 8-8\" />
  <path d=\"M14 7h7v7\" />
</svg>
"""

ICON_ALERT = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <path d=\"M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z\" />
  <path d=\"M12 9v4\" />
  <path d=\"M12 17h.01\" />
</svg>
"""

ICON_CLOCK = """
<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" class=\"w-4 h-4\" fill=\"none\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
  <circle cx=\"12\" cy=\"12\" r=\"10\" />
  <path d=\"M12 6v6l3 3\" />
</svg>
"""


def _get_menu_items() -> List[MenuItem]:
    perfil_url = reverse("accounts:perfil")
    configuracoes_url = reverse("configuracoes:configuracoes")
    nucleos_url = reverse("nucleos:list")
    eventos_url = reverse("eventos:lista")
    feed_url = reverse("feed:listar")

    perfil_children = [
        MenuItem(
            id="perfil_info",
            path=f"{perfil_url}?section=info",
            label="Informações",
            icon=ICON_INFO,
            permissions=["authenticated"],
        ),
        MenuItem(
            id="perfil_portfolio",
            path=f"{perfil_url}?section=portfolio",
            label="Portfólio",
            icon=ICON_BRIEFCASE,
            permissions=["authenticated"],
        ),
        MenuItem(
            id="perfil_conexoes",
            path=f"{perfil_url}?section=conexoes",
            label="Conexões",
            icon=ICON_LINK,
            permissions=["authenticated"],
        ),
    ]

    configuracoes_children = [
        MenuItem(
            id="configuracoes_seguranca",
            path=reverse("configuracoes:configuracoes_seguranca"),
            label="Segurança",
            icon=ICON_LOCK,
            permissions=["authenticated"],
        ),
        MenuItem(
            id="configuracoes_preferencias",
            path=reverse("configuracoes:configuracoes_preferencias"),
            label="Preferências",
            icon=ICON_SETTINGS,
            permissions=["authenticated"],
        ),
    ]

    nucleos_children = [
        MenuItem(
            id="nucleos_novo",
            path=reverse("nucleos:create"),
            label="Novo Núcleo",
            icon=ICON_PLUS,
            permissions=["admin"],
        )
    ]

    eventos_children = [
        MenuItem(
            id="eventos_calendario",
            path=reverse("eventos:calendario"),
            label="Calendário",
            icon=ICON_EVENTOS,
            permissions=[
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
        ),
        MenuItem(
            id="eventos_novo",
            path=reverse("eventos:evento_novo"),
            label="Novo Evento",
            icon=ICON_PLUS,
            permissions=["admin"],
        ),
    ]

    feed_children = [
        MenuItem(
            id="feed_nova_postagem",
            path=reverse("feed:nova_postagem"),
            label="Nova postagem",
            icon=ICON_PLUS,
            permissions=[
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
        ),
        MenuItem(
            id="feed_favoritos",
            path=reverse("feed:bookmarks"),
            label="Favoritos",
            icon=ICON_STAR,
            permissions=[
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
        ),
        MenuItem(
            id="feed_mural",
            path=reverse("feed:meu_mural"),
            label="Mural",
            icon=ICON_CHAT,
            permissions=[
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
        ),
    ]

    return [
        MenuItem(
            id="perfil",
            path=perfil_url,
            label="Perfil",
            icon=ICON_USER,
            permissions=["authenticated"],
            classes="flex items-center hover:text-primary transition",
            children=perfil_children,
        ),
        MenuItem("associados", reverse("associados_lista"), "Associados", ICON_USERS, ["admin", "coordenador"]),
        MenuItem(
            "nucleos",
            nucleos_url,
            "Núcleos",
            ICON_USERS,
            [
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
            children=nucleos_children,
        ),
        MenuItem(
            "meus_nucleos",
            reverse("nucleos:meus"),
            "Meus Núcleos",
            ICON_USERS,
            [
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
        ),
        MenuItem(
            "eventos",
            eventos_url,
            "Eventos",
            ICON_EVENTOS,
            [
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
            children=eventos_children,
        ),
        MenuItem(
            "feed",
            feed_url,
            "Feed",
            ICON_FEED,
            [
                "admin",
                "coordenador",
                "nucleado",
                "associado",
                "convidado",
            ],
            children=feed_children,
        ),
        MenuItem("organizacoes", reverse("organizacoes:list"), "Organizações", ICON_ORGS, ["root"]),
    MenuItem(
      "tokens",
      reverse("tokens:listar_convites"),
      "Tokens",
      ICON_TOKEN,
      ["root", "admin", "coordenador"],
      children=[
        MenuItem(
          id="tokens_gerar",
          path=reverse("tokens:gerar_convite"),
          label="Gerar Token",
          icon=ICON_PLUS,
          permissions=["root", "admin", "coordenador"],
        ),
        MenuItem(
          id="tokens_listar",
          path=reverse("tokens:listar_convites"),
          label="Listar Tokens",
          icon=ICON_TABLE,
          permissions=["root", "admin", "coordenador"],
        ),
      ],
    ),
    MenuItem(
      "configuracoes",
      reverse("configuracoes:configuracoes_seguranca"),
      "Configurações",
      ICON_CONFIG,
      ["authenticated"],
      "hover:text-primary transition",
      configuracoes_children,
    ),
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


def _user_has_permission(user, item: MenuItem) -> bool:
    perms = item.permissions or []
    if not perms:
        return True
    if "anonymous" in perms and not user.is_authenticated:
        return True
    if "authenticated" in perms and user.is_authenticated:
        return True
    if user.is_authenticated and user.user_type in perms:
        return True
    return False


def _filter_items(items: List[MenuItem], user) -> List[MenuItem]:
    filtered: List[MenuItem] = []
    for item in items:
        filtered_children = _filter_items(item.children, user) if item.children else []
        if _user_has_permission(user, item):
            filtered_item = replace(item, children=filtered_children or None)
            filtered.append(filtered_item)
    return filtered


def _mark_active(items: List[MenuItem], current_path: str, current_full_path: str) -> bool:
    any_active = False
    for item in items:
        child_active = False
        if item.children:
            child_active = _mark_active(item.children, current_path, current_full_path)
        is_current = current_path == item.path or current_full_path == item.path
        item.is_current = is_current
        item.has_active_child = child_active
        item.is_active = is_current or child_active
        item.is_expanded = item.is_active
        any_active = any_active or item.is_active
    return any_active
def build_menu(request) -> List[MenuItem]:
    """Retorna itens de menu filtrados por tipo de usuário."""

    items = _get_menu_items()
    user = request.user
    filtered = _filter_items(items, user)
    current_path = request.path
    current_full_path = request.get_full_path()
    _mark_active(filtered, current_path, current_full_path)
    return filtered
