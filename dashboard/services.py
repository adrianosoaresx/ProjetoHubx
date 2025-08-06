import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from chat.models import ChatMessage
from discussao.models import RespostaDiscussao, TopicoDiscussao
from empresas.models import Empresa
from feed.models import Post, Tag
from financeiro.models import LancamentoFinanceiro
from notificacoes.models import NotificationLog
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .utils import get_variation


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
    tags = (
        Tag.objects.filter(posts__in=posts)
        .annotate(total=Count("posts"))
        .order_by("-total")[:limite]
    )
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
    autores = (
        qs.values("autor_id", "autor__username")
        .annotate(total=Count("id"))
        .order_by("-total")[:limite]
    )
    result = [
        {"autor_id": a["autor_id"], "autor": a["autor__username"], "total": a["total"]}
        for a in autores
    ]
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
    def calcular_topicos_respostas_forum() -> Dict[str, int]:
        topicos = TopicoDiscussao.objects.count()
        respostas = RespostaDiscussao.objects.count()
        return {"topicos": topicos, "respostas": respostas}

    @staticmethod
    def calcular_posts_feed() -> int:
        return Post.objects.count()

    @staticmethod
    def calcular_mensagens_chat() -> int:
        return ChatMessage.objects.count()

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
        campo: str = "created",
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
        qs = NotificationLog.objects.select_related("template")
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
            "num_posts": (
                Post.objects.select_related("organizacao", "nucleo", "evento"),
                "created_at",
            ),
            "inscricoes_confirmadas": (
                InscricaoEvento.objects.select_related("evento").filter(status="confirmada"),
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
                if name in {"num_users", "num_eventos", "num_posts"}:
                    qs = qs.filter(organizacao_id=organizacao_id)
                elif name == "num_organizacoes":
                    qs = qs.filter(pk=organizacao_id)
                elif name == "num_nucleos":
                    qs = qs.filter(organizacao_id=organizacao_id)
                elif name == "num_empresas":
                    qs = qs.filter(usuario__organizacao_id=organizacao_id)
                elif name == "inscricoes_confirmadas":
                    qs = qs.filter(evento__organizacao_id=organizacao_id)
                elif name == "lancamentos_pendentes":
                    qs = qs.filter(centro_custo__organizacao_id=organizacao_id)
            if nucleo_id:
                if name == "num_users":
                    qs = qs.filter(nucleos__id=nucleo_id)
                if name == "num_nucleos":
                    qs = qs.filter(pk=nucleo_id)
                if name == "num_empresas":
                    qs = qs.filter(usuario__nucleos__id=nucleo_id)
                if name == "num_eventos":
                    qs = qs.filter(nucleo_id=nucleo_id)
                if name == "num_posts":
                    qs = qs.filter(nucleo_id=nucleo_id)
                if name == "inscricoes_confirmadas":
                    qs = qs.filter(evento__nucleo_id=nucleo_id)
                if name == "lancamentos_pendentes":
                    qs = qs.filter(centro_custo__nucleo_id=nucleo_id)
            if evento_id:
                if name == "num_eventos":
                    qs = qs.filter(pk=evento_id)
                if name == "num_posts":
                    qs = qs.filter(evento_id=evento_id)
                if name == "inscricoes_confirmadas":
                    qs = qs.filter(evento_id=evento_id)
                if name == "lancamentos_pendentes":
                    qs = qs.filter(centro_custo__evento_id=evento_id)
            query_map[name] = (qs, campo)

        metrics = {
            name: DashboardService.calcular_crescimento(qs, inicio, fim, campo=campo)
            for name, (qs, campo) in query_map.items()
        }

        cache.set(cache_key, metrics, 300)
        return metrics
