from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from chat.models import ChatMessage
from discussao.models import RespostaDiscussao, TopicoDiscussao
from feed.models import Post
from empresas.models import Empresa
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
        campo: str = "created_at",
    ) -> Dict[str, float]:
        atual = queryset.filter(**{f"{campo}__gte": inicio, f"{campo}__lte": fim}).count()
        delta = fim - inicio
        prev_inicio = inicio - delta
        prev_fim = inicio - timedelta(seconds=1)
        anterior = queryset.filter(**{f"{campo}__gte": prev_inicio, f"{campo}__lte": prev_fim}).count()
        crescimento = get_variation(anterior, atual) if anterior else (100.0 if atual else 0.0)
        return {"total": atual, "crescimento": crescimento}


class DashboardMetricsService:
    @staticmethod
    def get_metrics(
        user: User,
        periodo: str = "mensal",
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Return dashboard metrics, cached for 5 minutes."""
        inicio, fim = DashboardService.get_period_range(periodo, inicio, fim)
        cache_key = f"dashboard_metrics_{user.pk}_{periodo}_{inicio.isoformat()}_{fim.isoformat()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        qs_users = User.objects.all()
        qs_orgs = Organizacao.objects.all()
        qs_nucleos = Nucleo.objects.all()
        qs_empresas = Empresa.objects.all()
        qs_eventos = Evento.objects.all()

        if user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            org = user.organizacao
            qs_users = qs_users.filter(organizacao=org)
            qs_orgs = qs_orgs.filter(pk=getattr(org, "pk", None))
            qs_nucleos = qs_nucleos.filter(organizacao=org)
            qs_empresas = qs_empresas.filter(usuario__organizacao=org)
            qs_eventos = qs_eventos.filter(organizacao=org)

        metrics = {
            "num_users": DashboardService.calcular_crescimento(qs_users, inicio, fim),
            "num_organizacoes": DashboardService.calcular_crescimento(qs_orgs, inicio, fim),
            "num_nucleos": DashboardService.calcular_crescimento(qs_nucleos, inicio, fim),
            "num_empresas": DashboardService.calcular_crescimento(qs_empresas, inicio, fim),
            "num_eventos": DashboardService.calcular_crescimento(qs_eventos, inicio, fim),
        }
        cache.set(cache_key, metrics, 300)
        return metrics
