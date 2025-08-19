import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from audit.models import AuditLog
from audit.services import hash_ip, log_audit
from chat.models import ChatMessage
from discussao.models import RespostaDiscussao, TopicoDiscussao
from empresas.models import Empresa
from feed.models import Post, PostView, Reacao, Tag
from financeiro.models import LancamentoFinanceiro
from notificacoes.models import NotificationLog, NotificationStatus
from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from tokens.models import TokenAcesso as InviteToken
from tokens.models import TokenUsoLog as UserToken

from .utils import get_variation
from .models import (
    Achievement,
    DashboardConfig,
    DashboardFilter,
    DashboardLayout,
    UserAchievement,
)


def log_filter_action(
    user,
    action: str,
    filtro: DashboardFilter,
    ip_address: str,
    status: str = AuditLog.Status.SUCCESS,
    metadata: dict | None = None,
) -> None:
    """Registra auditoria para ações relacionadas a filtros."""
    if metadata is None:
        metadata = {"filtros": filtro.filtros}
    log_audit(
        user=user,
        action=action,
        object_type="DashboardFilter",
        object_id=str(filtro.pk),
        ip_hash=hash_ip(ip_address or ""),
        status=status,
        metadata=metadata,
    )


def log_layout_action(
    user,
    action: str,
    layout: DashboardLayout,
    ip_address: str,
    status: str = AuditLog.Status.SUCCESS,
    metadata: dict | None = None,
) -> None:
    """Registra auditoria para ações relacionadas a layouts."""
    if metadata is None:
        metadata = {"nome": layout.nome, "publico": layout.publico}
    log_audit(
        user=user,
        action=action,
        object_type="DashboardLayout",
        object_id=str(layout.pk),
        ip_hash=hash_ip(ip_address or ""),
        status=status,
        metadata=metadata,
    )


def _apply_feed_filters(queryset, organizacao=None, data_inicio=None, data_fim=None):
    """Aplicar filtros comuns para consultas do feed."""
    if organizacao:
        queryset = queryset.filter(organizacao_id=organizacao)
    if data_inicio:
        queryset = queryset.filter(created_at__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(created_at__lte=data_fim)
    return queryset


def get_feed_counts(
    organizacao: Optional[int] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
):
    """Retorna contagens agregadas de posts, curtidas e comentários."""
    cache_key = f"feed-counts-{organizacao}-{data_inicio}-{data_fim}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    qs = _apply_feed_filters(Post.objects.all(), organizacao, data_inicio, data_fim)
    aggregates = qs.aggregate(
        total_posts=Count("id"),
        total_likes=Count("likes", distinct=True),
        total_comments=Count("comments", distinct=True),
    )
    by_type = qs.values("tipo_feed").annotate(total=Count("id")).order_by()
    result = {
        **aggregates,
        "posts_by_type": {row["tipo_feed"]: row["total"] for row in by_type},
    }
    cache.set(cache_key, result, 300)
    return result


def get_top_tags(
    organizacao: Optional[int] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    limite: int = 5,
):
    """Retorna as tags mais utilizadas no feed."""
    cache_key = f"feed-top-tags-{organizacao}-{data_inicio}-{data_fim}-{limite}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    posts = _apply_feed_filters(Post.objects.all(), organizacao, data_inicio, data_fim)
    tags = Tag.objects.filter(posts__in=posts).annotate(total=Count("posts")).order_by("-total")[:limite]
    result = [{"tag": t.nome, "total": t.total} for t in tags]
    cache.set(cache_key, result, 300)
    return result


def get_top_authors(
    organizacao: Optional[int] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    limite: int = 5,
):
    """Retorna os autores com mais posts no período."""
    cache_key = f"feed-top-authors-{organizacao}-{data_inicio}-{data_fim}-{limite}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    qs = _apply_feed_filters(Post.objects.select_related("autor"), organizacao, data_inicio, data_fim)
    autores = qs.values("autor_id", "autor__username").annotate(total=Count("id")).order_by("-total")[:limite]
    result = [{"autor_id": a["autor_id"], "autor": a["autor__username"], "total": a["total"]} for a in autores]
    cache.set(cache_key, result, 300)
    return result


class DashboardService:
    @staticmethod
    def calcular_distribuicao_usuarios(tipo: Optional[str] = None, status: Optional[str] = None) -> Dict[str, int]:
        query = User.objects.all()
        if tipo:
            query = query.filter(tipo=tipo)
        if status:
            query = query.filter(is_active=(status == "ativo"))
        return query.values("tipo").annotate(total=Count("id"))

    @staticmethod
    def calcular_eventos_por_status() -> Dict[str, int]:
        return Evento.objects.values("status").annotate(total=Count("id"))

    @staticmethod
    def calcular_inscricoes_eventos() -> Dict[str, Dict[str, float]]:
        inscricoes = InscricaoEvento.objects.aggregate(
            total=Count("id"),
            confirmados=Count("id", filter=Q(status="confirmada")),
            avaliacao_media=Avg("evento__feedbacknota__nota"),
        )
        return inscricoes

    @staticmethod
    def calcular_posts_feed(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
    ) -> int:
        qs = Post.objects.select_related(
            "autor__organizacao",
            "organizacao",
            "nucleo",
            "evento",
        )
        if organizacao_id:
            qs = qs.filter(organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(nucleo_id=nucleo_id)
        if evento_id:
            qs = qs.filter(evento_id=evento_id)
        return qs.count()

    @staticmethod
    def calcular_posts_feed_24h(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
    ) -> int:
        desde = timezone.now() - timedelta(days=1)
        qs = Post.objects.select_related(
            "autor__organizacao",
            "organizacao",
            "nucleo",
            "evento",
        ).filter(created_at__gte=desde)
        if organizacao_id:
            qs = qs.filter(organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(nucleo_id=nucleo_id)
        if evento_id:
            qs = qs.filter(evento_id=evento_id)
        return qs.count()


    @staticmethod
    def calcular_topicos_discussao(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
    ) -> int:
        qs = TopicoDiscussao.objects.select_related(
            "categoria__organizacao",
            "nucleo",
            "evento",
        )
        if organizacao_id:
            qs = qs.filter(categoria__organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(Q(nucleo_id=nucleo_id) | Q(categoria__nucleo_id=nucleo_id))
        if evento_id:
            qs = qs.filter(Q(evento_id=evento_id) | Q(categoria__evento_id=evento_id))
        return qs.count()

    @staticmethod
    def calcular_respostas_discussao(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
    ) -> int:
        qs = RespostaDiscussao.objects.select_related(
            "topico__categoria__organizacao",
            "topico__nucleo",
            "topico__evento",
        )
        if organizacao_id:
            qs = qs.filter(topico__categoria__organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(Q(topico__nucleo_id=nucleo_id) | Q(topico__categoria__nucleo_id=nucleo_id))
        if evento_id:
            qs = qs.filter(Q(topico__evento_id=evento_id) | Q(topico__categoria__evento_id=evento_id))
        return qs.count()

    @staticmethod
    def calcular_mensagens_chat(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> int:
        """Count chat messages applying optional filters."""
        qs = ChatMessage.objects.select_related("channel")
        if data_inicio:
            qs = qs.filter(created_at__gte=data_inicio)
        if data_fim:
            qs = qs.filter(created_at__lte=data_fim)
        if evento_id:
            qs = qs.filter(channel__contexto_tipo="evento", channel__contexto_id=evento_id)
        elif nucleo_id:
            qs = qs.filter(channel__contexto_tipo="nucleo", channel__contexto_id=nucleo_id)
        elif organizacao_id:
            qs = qs.filter(channel__contexto_tipo="organizacao", channel__contexto_id=organizacao_id)
        return qs.count()

    @staticmethod
    def calcular_reacoes_feed(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> dict[str, int]:
        qs = Reacao.objects.select_related("post")
        if data_inicio:
            qs = qs.filter(created_at__gte=data_inicio)
        if data_fim:
            qs = qs.filter(created_at__lte=data_fim)
        if organizacao_id:
            qs = qs.filter(post__organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(post__nucleo_id=nucleo_id)
        if evento_id:
            qs = qs.filter(post__evento_id=evento_id)
        return {
            "curtidas": qs.filter(vote=Reacao.Tipo.CURTIDA).count(),
            "compartilhamentos": qs.filter(vote=Reacao.Tipo.COMPARTILHAMENTO).count(),
        }

    @staticmethod
    def calcular_tempo_medio_leitura(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> float:
        qs = PostView.objects.select_related("post")
        if data_inicio:
            qs = qs.filter(opened_at__gte=data_inicio)
        if data_fim:
            qs = qs.filter(closed_at__lte=data_fim)
        if organizacao_id:
            qs = qs.filter(post__organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(post__nucleo_id=nucleo_id)
        if evento_id:
            qs = qs.filter(post__evento_id=evento_id)
        avg = qs.aggregate(dur=Avg(F("closed_at") - F("opened_at")))["dur"]
        return float(avg.total_seconds()) if avg else 0.0

    @staticmethod
    def posts_populares_24h(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        evento_id: Optional[int] = None,
        limite: int = 5,
    ) -> list[dict[str, object]]:
        desde = timezone.now() - timedelta(days=1)
        qs = Reacao.objects.select_related("post").filter(vote=Reacao.Tipo.CURTIDA, created_at__gte=desde)
        if organizacao_id:
            qs = qs.filter(post__organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(post__nucleo_id=nucleo_id)
        if evento_id:
            qs = qs.filter(post__evento_id=evento_id)
        top = qs.values("post_id").annotate(total=Count("id")).order_by("-total")[:limite]
        return [{"post_id": str(item["post_id"]), "likes": item["total"]} for item in top]

    @staticmethod
    def contar_tokens_gerados(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> int:
        qs = InviteToken.objects.all()
        if data_inicio:
            qs = qs.filter(created_at__gte=data_inicio)
        if data_fim:
            qs = qs.filter(created_at__lte=data_fim)
        if organizacao_id:
            qs = qs.filter(organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(nucleos__id=nucleo_id)
        return qs.count()

    @staticmethod
    def contar_tokens_consumidos(
        organizacao_id: Optional[int] = None,
        nucleo_id: Optional[int] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
    ) -> int:
        qs = UserToken.objects.filter(acao=UserToken.Acao.USO).select_related("token")
        if data_inicio:
            qs = qs.filter(created_at__gte=data_inicio)
        if data_fim:
            qs = qs.filter(created_at__lte=data_fim)
        if organizacao_id:
            qs = qs.filter(token__organizacao_id=organizacao_id)
        if nucleo_id:
            qs = qs.filter(token__nucleos__id=nucleo_id)
        return qs.count()

    @staticmethod
    def calcular_valores_eventos() -> Dict[str, float]:
        valores = {
            "valor_arrecadado": InscricaoEvento.objects.aggregate(Sum("valor_pago"))["valor_pago__sum"],
            "valor_gasto": Evento.objects.aggregate(Sum("orcamento"))["orcamento__sum"],
        }
        return valores

    @staticmethod
    def aplicar_filtros(
        queryset,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        organizacao: Optional[int] = None,
        nucleo: Optional[int] = None,
    ):
        if data_inicio:
            queryset = queryset.filter(data__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        if organizacao:
            queryset = queryset.filter(organizacao_id=organizacao)
        if nucleo:
            queryset = queryset.filter(nucleo_id=nucleo)
        return queryset

    @staticmethod
    def inscricoes_por_periodo(
        periodo: str = "mensal", inicio: Optional[datetime] = None, fim: Optional[datetime] = None
    ):
        inicio, fim = DashboardService.get_period_range(periodo, inicio, fim)
        qs = InscricaoEvento.objects.all()
        return DashboardService.calcular_crescimento(qs, inicio, fim)

    @staticmethod
    def get_period_range(
        periodo: str, inicio: Optional[datetime] = None, fim: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        if not inicio and not fim:
            hoje = datetime.today().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            inicio = hoje
        if periodo == "mensal":
            fim = inicio + relativedelta(months=1) - timedelta(seconds=1)
        elif periodo == "trimestral":
            fim = inicio + relativedelta(months=3) - timedelta(seconds=1)
        elif periodo == "semestral":
            fim = inicio + relativedelta(months=6) - timedelta(seconds=1)
        elif periodo == "anual":
            fim = inicio + relativedelta(years=1) - timedelta(seconds=1)
        else:
            fim = fim or inicio + relativedelta(months=1) - timedelta(seconds=1)
        return inicio, fim

    @staticmethod
    def calcular_crescimento(
        queryset,
        inicio: datetime,
        fim: datetime,
        campo: str = "created_at",
    ) -> Dict[str, float]:
        """Calcule crescimento utilizando uma única consulta."""
        delta = fim - inicio
        prev_inicio = inicio - delta
        prev_fim = inicio - timedelta(seconds=1)

        aggregates = queryset.aggregate(
            atual=Count("id", filter=Q(**{f"{campo}__gte": inicio, f"{campo}__lte": fim})),
            anterior=Count("id", filter=Q(**{f"{campo}__gte": prev_inicio, f"{campo}__lte": prev_fim})),
        )
        atual = aggregates["atual"] or 0
        anterior = aggregates["anterior"] or 0
        crescimento = get_variation(anterior, atual) if anterior else (100.0 if atual else 0.0)
        return {"total": atual, "crescimento": crescimento}

    @staticmethod
    def ultimos_lancamentos(user: User, limit: int = 5):
        qs = LancamentoFinanceiro.objects.select_related("centro_custo")
        if user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            qs = qs.filter(centro_custo__organizacao=user.organizacao)
        return qs.order_by("-data_lancamento")[:limit]

    @staticmethod
    def ultimas_notificacoes(user: User, limit: int = 5):
        qs = NotificationLog.objects.select_related("template").exclude(status=NotificationStatus.LIDA)
        if user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            qs = qs.filter(user=user)
        return qs.order_by("-data_envio")[:limit]

    @staticmethod
    def tarefas_pendentes(user: User, limit: int = 5):
        qs = LancamentoFinanceiro.objects.filter(status=LancamentoFinanceiro.Status.PENDENTE)
        if user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            qs = qs.filter(centro_custo__organizacao=user.organizacao)
        return qs.order_by("data_vencimento")[:limit]

    @staticmethod
    def proximos_eventos(user: User, limit: int = 5):
        qs = Evento.objects.filter(data_inicio__gte=timezone.now())
        if user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            qs = qs.filter(organizacao=user.organizacao)
        return qs.order_by("data_inicio")[:limit]

    @staticmethod
    def medias_globais(metricas: Optional[list[str]] = None, por: str = "organizacao"):
        query_map = {
            "num_users": User.objects.all(),
            "num_organizacoes": Organizacao.objects.all(),
            "num_nucleos": Nucleo.objects.all(),
            "num_empresas": Empresa.objects.select_related("usuario", "usuario__organizacao"),
            "num_eventos": Evento.objects.select_related("nucleo"),
            "num_posts_feed_total": Post.objects.all(),
            "num_mensagens_chat": ChatMessage.objects.all(),
            "num_topicos": TopicoDiscussao.objects.all(),
            "num_respostas": RespostaDiscussao.objects.all(),
        }
        if metricas:
            query_map = {k: v for k, v in query_map.items() if k in metricas}
        divisor = Organizacao.objects.count() if por == "organizacao" else Nucleo.objects.count()
        divisor = divisor or 1
        medias = {}
        for name, qs in query_map.items():
            medias[name] = qs.count() / divisor
        return medias


class DashboardMetricsService:
    @staticmethod
    def get_metrics(
        user: User,
        periodo: str = "mensal",
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None,
        escopo: str = "auto",
        **filters,
    ) -> Dict[str, Dict[str, float]]:
        """Return dashboard metrics, cached for 5 minutes."""
        valid_periodos = {"mensal", "trimestral", "semestral", "anual"}
        if periodo not in valid_periodos:
            raise ValueError("Período inválido")
        if isinstance(inicio, str):
            try:
                inicio = datetime.fromisoformat(inicio)
            except ValueError:
                raise ValueError("data_inicio inválida")
        if isinstance(fim, str):
            try:
                fim = datetime.fromisoformat(fim)
            except ValueError:
                raise ValueError("data_fim inválida")
        inicio, fim = DashboardService.get_period_range(periodo, inicio, fim)

        cache_filters = {
            "periodo": periodo,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            **{k: str(v) for k, v in filters.items()},
        }
        cache_key = f"dashboard-{escopo}-{json.dumps(cache_filters, sort_keys=True)}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        organizacao_id = filters.get("organizacao_id")
        nucleo_id = filters.get("nucleo_id")
        evento_id = filters.get("evento_id")

        # determine filtering based on scope
        if escopo == "auto":
            if user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
                organizacao_id = organizacao_id or getattr(user.organizacao, "pk", None)
            elif user.user_type not in {UserType.ROOT}:
                # for clientes limit to user's own data
                organizacao_id = getattr(user.organizacao, "pk", None)
        elif escopo == "organizacao" and organizacao_id:
            if user.user_type not in {UserType.ROOT, UserType.ADMIN}:
                raise PermissionError("Escopo de organização não permitido")
        elif escopo == "nucleo" and nucleo_id:
            nucleo = Nucleo.objects.filter(pk=nucleo_id).first()
            if not nucleo:
                raise ValueError("Núcleo inválido")
            if user.user_type not in {UserType.ROOT, UserType.ADMIN} and not nucleo.membros.filter(pk=user.pk).exists():
                raise PermissionError("Acesso negado ao núcleo")
            organizacao_id = organizacao_id or nucleo.organizacao_id
        elif escopo == "evento" and evento_id:
            evento = Evento.objects.filter(pk=evento_id).first()
            if not evento:
                raise ValueError("Evento inválido")
            if user.user_type not in {UserType.ROOT, UserType.ADMIN} and not (
                evento.coordenador_id == user.pk or evento.nucleo and evento.nucleo.membros.filter(pk=user.pk).exists()
            ):
                raise PermissionError("Acesso negado ao evento")
            organizacao_id = organizacao_id or evento.organizacao_id
            nucleo_id = nucleo_id or evento.nucleo_id
        elif escopo not in {"auto", "global", "organizacao", "nucleo", "evento"}:
            raise ValueError("Escopo inválido")

        metricas = filters.get("metricas")

        query_map = {
            "num_users": (User.objects.all(), "created_at"),
            "num_organizacoes": (Organizacao.objects.all(), "created_at"),
            "num_nucleos": (Nucleo.objects.all(), "created_at"),
            "num_empresas": (
                Empresa.objects.select_related("usuario", "usuario__organizacao"),
                "created_at",
            ),
            "num_eventos": (Evento.objects.select_related("nucleo"), "created"),
            "num_posts_feed_total": (
                Post.objects.select_related("organizacao", "nucleo", "evento", "autor__organizacao"),
                "created_at",
            ),
            "num_mensagens_chat": (
                ChatMessage.objects.select_related("channel"),
                "created",
            ),
            "num_topicos": (
                TopicoDiscussao.objects.select_related(
                    "categoria__organizacao",
                    "nucleo",
                    "evento",
                ),
                "created",
            ),
            "num_respostas": (
                RespostaDiscussao.objects.select_related(
                    "topico__categoria__organizacao",
                    "topico__nucleo",
                    "topico__evento",
                ),
                "created",
            ),
            "lancamentos_pendentes": (
                LancamentoFinanceiro.objects.select_related("centro_custo").filter(
                    status=LancamentoFinanceiro.Status.PENDENTE
                ),
                "data_lancamento",
            ),
        }

        if metricas:
            query_map = {k: v for k, v in query_map.items() if k in metricas}

        for name, (qs, campo) in list(query_map.items()):
            if organizacao_id:
                if name in {"num_users", "num_eventos", "num_posts_feed_total"}:
                    qs = qs.filter(organizacao_id=organizacao_id)
                elif name == "num_organizacoes":
                    qs = qs.filter(pk=organizacao_id)
                elif name == "num_nucleos":
                    qs = qs.filter(organizacao_id=organizacao_id)
                elif name == "num_empresas":
                    qs = qs.filter(usuario__organizacao_id=organizacao_id)
                elif name == "lancamentos_pendentes":
                    qs = qs.filter(centro_custo__organizacao_id=organizacao_id)
                elif name == "num_topicos":
                    qs = qs.filter(categoria__organizacao_id=organizacao_id)
                elif name == "num_respostas":
                    qs = qs.filter(topico__categoria__organizacao_id=organizacao_id)
                elif name == "num_mensagens_chat":
                    qs = qs.filter(channel__contexto_tipo="organizacao", channel__contexto_id=organizacao_id)
            if nucleo_id:
                if name == "num_users":
                    qs = qs.filter(nucleos__id=nucleo_id)
                if name == "num_nucleos":
                    qs = qs.filter(pk=nucleo_id)
                if name == "num_empresas":
                    qs = qs.filter(usuario__nucleos__id=nucleo_id)
                if name == "num_eventos":
                    qs = qs.filter(nucleo_id=nucleo_id)
                if name == "num_posts_feed_total":
                    qs = qs.filter(nucleo_id=nucleo_id)
                if name == "lancamentos_pendentes":
                    qs = qs.filter(centro_custo__nucleo_id=nucleo_id)
                if name == "num_topicos":
                    qs = qs.filter(Q(nucleo_id=nucleo_id) | Q(categoria__nucleo_id=nucleo_id))
                if name == "num_respostas":
                    qs = qs.filter(Q(topico__nucleo_id=nucleo_id) | Q(topico__categoria__nucleo_id=nucleo_id))
                if name == "num_mensagens_chat":
                    qs = qs.filter(channel__contexto_tipo="nucleo", channel__contexto_id=nucleo_id)
            if evento_id:
                if name == "num_eventos":
                    qs = qs.filter(pk=evento_id)
                if name == "num_posts_feed_total":
                    qs = qs.filter(evento_id=evento_id)
                if name == "lancamentos_pendentes":
                    qs = qs.filter(centro_custo__evento_id=evento_id)
                if name == "num_topicos":
                    qs = qs.filter(Q(evento_id=evento_id) | Q(categoria__evento_id=evento_id))
                if name == "num_respostas":
                    qs = qs.filter(Q(topico__evento_id=evento_id) | Q(topico__categoria__evento_id=evento_id))
                if name == "num_mensagens_chat":
                    qs = qs.filter(channel__contexto_tipo="evento", channel__contexto_id=evento_id)
            query_map[name] = (qs, campo)

        metrics = {
            name: DashboardService.calcular_crescimento(qs, inicio, fim, campo=campo)
            for name, (qs, campo) in query_map.items()
        }

        if not metricas or "inscricoes_confirmadas" in metricas:
            qs = InscricaoEvento.objects.select_related("evento").filter(status="confirmada")
            if organizacao_id:
                qs = qs.filter(evento__organizacao_id=organizacao_id)
            if nucleo_id:
                qs = qs.filter(evento__nucleo_id=nucleo_id)
            if evento_id:
                qs = qs.filter(evento_id=evento_id)
            metrics["inscricoes_confirmadas"] = {"total": qs.count(), "crescimento": 0.0}

        if not metricas or "num_posts_feed_recent" in metricas:
            metrics["num_posts_feed_recent"] = {
                "total": DashboardService.calcular_posts_feed_24h(
                    organizacao_id=organizacao_id,
                    nucleo_id=nucleo_id,
                    evento_id=evento_id,
                ),
                "crescimento": 0.0,
            }

        if not metricas or {"total_curtidas", "total_compartilhamentos"} & set(metricas or []):
            reacoes = DashboardService.calcular_reacoes_feed(
                organizacao_id=organizacao_id,
                nucleo_id=nucleo_id,
                evento_id=evento_id,
                data_inicio=inicio,
                data_fim=fim,
            )
            if not metricas or "total_curtidas" in metricas:
                metrics["total_curtidas"] = {"total": reacoes["curtidas"], "crescimento": 0.0}
            if not metricas or "total_compartilhamentos" in metricas:
                metrics["total_compartilhamentos"] = {
                    "total": reacoes["compartilhamentos"],
                    "crescimento": 0.0,
                }

        if not metricas or "tempo_medio_leitura" in metricas:
            metrics["tempo_medio_leitura"] = {
                "total": DashboardService.calcular_tempo_medio_leitura(
                    organizacao_id=organizacao_id,
                    nucleo_id=nucleo_id,
                    evento_id=evento_id,
                    data_inicio=inicio,
                    data_fim=fim,
                ),
                "crescimento": 0.0,
            }

        if not metricas or "posts_populares_24h" in metricas:
            metrics["posts_populares_24h"] = {
                "total": DashboardService.posts_populares_24h(
                    organizacao_id=organizacao_id,
                    nucleo_id=nucleo_id,
                    evento_id=evento_id,
                ),
                "crescimento": 0.0,
            }

        if not metricas or "tokens_gerados" in metricas:
            metrics["tokens_gerados"] = {
                "total": DashboardService.contar_tokens_gerados(
                    organizacao_id=organizacao_id,
                    nucleo_id=nucleo_id,
                    data_inicio=inicio,
                    data_fim=fim,
                ),
                "crescimento": 0.0,
            }

        if not metricas or "tokens_consumidos" in metricas:
            metrics["tokens_consumidos"] = {
                "total": DashboardService.contar_tokens_consumidos(
                    organizacao_id=organizacao_id,
                    nucleo_id=nucleo_id,
                    data_inicio=inicio,
                    data_fim=fim,
                ),
                "crescimento": 0.0,
            }

        cache.set(cache_key, metrics, 300)
        return metrics

def check_achievements(user) -> None:
    """Verifica e registra conquistas atingidas pelo usuário."""

    achieved = set(
        UserAchievement.objects.filter(user=user).values_list("achievement__code", flat=True)
    )
    achievements = {a.code: a for a in Achievement.objects.all()}

    if (
        "100_inscricoes" in achievements
        and "100_inscricoes" not in achieved
        and InscricaoEvento.objects.filter(user=user).count() >= 100
    ):
        UserAchievement.objects.create(user=user, achievement=achievements["100_inscricoes"])

    if (
        "5_dashboards" in achievements
        and "5_dashboards" not in achieved
        and DashboardConfig.objects.filter(user=user).count() >= 5
    ):
        UserAchievement.objects.create(user=user, achievement=achievements["5_dashboards"])
