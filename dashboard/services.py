from datetime import datetime, timedelta
import json
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
from feed.models import Post
from financeiro.models import LancamentoFinanceiro
from notificacoes.models import NotificationLog
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .utils import get_variation


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
        atual = queryset.filter(**{f"{campo}__gte": inicio, f"{campo}__lte": fim}).count()
        delta = fim - inicio
        prev_inicio = inicio - delta
        prev_fim = inicio - timedelta(seconds=1)
        anterior = queryset.filter(**{f"{campo}__gte": prev_inicio, f"{campo}__lte": prev_fim}).count()
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
        inicio, fim = DashboardService.get_period_range(periodo, inicio, fim)

        cache_filters = {
            "periodo": periodo,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            **{k: str(v) for k, v in filters.items()},
        }
        cache_key = f"dashboard-{user.id}-{escopo}-{json.dumps(cache_filters, sort_keys=True)}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        qs_users = User.objects.all()
        qs_orgs = Organizacao.objects.all()
        qs_nucleos = Nucleo.objects.all()
        qs_empresas = Empresa.objects.all()
        qs_eventos = Evento.objects.all()
        qs_posts = Post.objects.all()

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

        if organizacao_id:
            qs_users = qs_users.filter(organizacao_id=organizacao_id)
            qs_orgs = qs_orgs.filter(pk=organizacao_id)
            qs_nucleos = qs_nucleos.filter(organizacao_id=organizacao_id)
            qs_empresas = qs_empresas.filter(usuario__organizacao_id=organizacao_id)
            qs_eventos = qs_eventos.filter(organizacao_id=organizacao_id)
            qs_posts = qs_posts.filter(organizacao_id=organizacao_id)

        if nucleo_id:
            qs_users = qs_users.filter(nucleos__id=nucleo_id)
            qs_nucleos = qs_nucleos.filter(pk=nucleo_id)
            qs_empresas = qs_empresas.filter(usuario__nucleos__id=nucleo_id)
            qs_eventos = qs_eventos.filter(nucleo_id=nucleo_id)
            qs_posts = qs_posts.filter(nucleo_id=nucleo_id)

        if evento_id:
            qs_eventos = qs_eventos.filter(pk=evento_id)
            qs_posts = qs_posts.filter(evento_id=evento_id)

        metrics = {
            "num_users": DashboardService.calcular_crescimento(qs_users, inicio, fim, campo="created_at"),
            "num_organizacoes": DashboardService.calcular_crescimento(qs_orgs, inicio, fim, campo="created_at"),
            "num_nucleos": DashboardService.calcular_crescimento(qs_nucleos, inicio, fim, campo="created_at"),
            "num_empresas": DashboardService.calcular_crescimento(qs_empresas, inicio, fim, campo="created_at"),
            "num_eventos": DashboardService.calcular_crescimento(qs_eventos, inicio, fim, campo="created"),
            "num_posts": DashboardService.calcular_crescimento(qs_posts, inicio, fim, campo="created_at"),
        }

        metricas = filters.get("metricas")
        if metricas:
            metrics = {k: v for k, v in metrics.items() if k in metricas}

        cache.set(cache_key, metrics, 300)
        return metrics
