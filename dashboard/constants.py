from django.utils.translation import gettext_lazy as _

METRICAS_INFO = {
    "num_users": {"label": _("Usuários"), "icon": "fa-users"},
    "num_organizacoes": {"label": _("Organizações"), "icon": "fa-building"},
    "num_nucleos": {"label": _("Núcleos"), "icon": "fa-users-rectangle"},
    "num_empresas": {"label": _("Empresas"), "icon": "fa-city"},
    "num_eventos": {"label": _("Eventos"), "icon": "fa-calendar"},
    "num_posts_feed_total": {"label": _("Posts (Total)"), "icon": "fa-newspaper"},
    "num_posts_feed_recent": {"label": _("Posts (24h)"), "icon": "fa-clock"},
    "num_topicos": {"label": _("Tópicos"), "icon": "fa-comments"},
    "num_respostas": {"label": _("Respostas"), "icon": "fa-reply"},
    "num_mensagens_chat": {"label": _("Mensagens de chat"), "icon": "fa-comments"},
    "total_curtidas": {"label": _("Curtidas"), "icon": "fa-thumbs-up"},
    "total_compartilhamentos": {"label": _("Compartilhamentos"), "icon": "fa-share"},
    "tempo_medio_leitura": {
        "label": _("Tempo médio de leitura (s)"),
        "icon": "fa-book-open",
    },
    "inscricoes_confirmadas": {
        "label": _("Inscrições confirmadas"),
        "icon": "fa-user-check",
    },
    "lancamentos_pendentes": {
        "label": _("Lançamentos pendentes"),
        "icon": "fa-hourglass-half",
    },
    "posts_populares_24h": {"label": _("Posts populares 24h"), "icon": "fa-fire"},
    "tokens_gerados": {"label": _("Tokens gerados"), "icon": "fa-ticket"},
    "tokens_consumidos": {"label": _("Tokens consumidos"), "icon": "fa-ticket"},
}
