from django.utils.translation import gettext_lazy as _

METRICAS_INFO = {
    "num_users": {"label": _("Usuários"), "icon": "users"},
    "num_organizacoes": {"label": _("Organizações"), "icon": "building-2"},
    "num_nucleos": {"label": _("Núcleos"), "icon": "users-round"},
    "num_empresas": {"label": _("Empresas"), "icon": "landmark"},
    "num_eventos": {"label": _("Eventos"), "icon": "calendar"},
    "num_posts_feed_total": {"label": _("Posts (Total)"), "icon": "newspaper"},
    "num_posts_feed_recent": {"label": _("Posts (24h)"), "icon": "clock"},
    "num_topicos": {"label": _("Tópicos"), "icon": "messages-square"},
    "num_respostas": {"label": _("Respostas"), "icon": "reply"},
    "total_curtidas": {"label": _("Curtidas"), "icon": "thumbs-up"},
    "total_compartilhamentos": {"label": _("Compartilhamentos"), "icon": "share-2"},
    "tempo_medio_leitura": {
        "label": _("Tempo médio de leitura (s)"),
        "icon": "book-open",
    },
    "inscricoes_confirmadas": {
        "label": _("Inscrições confirmadas"),
        "icon": "user-check",
    },
    "lancamentos_pendentes": {
        "label": _("Lançamentos pendentes"),
        "icon": "hourglass",
    },
    "posts_populares_24h": {"label": _("Posts populares 24h"), "icon": "flame"},
    "tokens_gerados": {"label": _("Tokens gerados"), "icon": "ticket"},
    "tokens_consumidos": {"label": _("Tokens consumidos"), "icon": "ticket"},
}
