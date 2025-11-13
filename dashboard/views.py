from copy import deepcopy
from decimal import Decimal
import json
from itertools import zip_longest
from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from core.permissions import AdminOrOperatorRequiredMixin

from eventos.models import Evento
from eventos.models import FeedbackNota, InscricaoEvento

from accounts.models import UserType
from feed.models import Bookmark
from nucleos.models import Nucleo

from .services import (
    MEMBROS_NUCLEADOS_LABEL,
    build_chart_payload,
    build_time_series_chart,
    calculate_event_status_totals,
    calculate_events_by_nucleo,
    calculate_membership_totals,
    calculate_monthly_membros,
    calculate_monthly_events,
    calculate_monthly_event_registrations,
    calculate_monthly_nucleados,
    calculate_monthly_registration_values,
    count_confirmed_event_registrations,
)


class AdminDashboardView(LoginRequiredMixin, AdminOrOperatorRequiredMixin, TemplateView):
    """View principal do painel administrativo."""

    template_name = "dashboard/admin_dashboard.html"
    DEFAULT_MONTHS = 12
    PERIOD_CHOICES: tuple[int, ...] = (3, 6, 12, 24)

    def _resolve_months(self) -> int:
        """Obtém o número de meses válido informado via query string."""

        raw_months = self.request.GET.get("months")
        if not raw_months:
            return self.DEFAULT_MONTHS

        try:
            months = int(raw_months)
        except (TypeError, ValueError):
            return self.DEFAULT_MONTHS

        if months not in self.PERIOD_CHOICES:
            return self.DEFAULT_MONTHS
        return months

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        organizacao = getattr(self.request.user, "organizacao", None)
        months = self._resolve_months()

        membership_totals = calculate_membership_totals(organizacao)
        event_totals = calculate_event_status_totals(organizacao)
        confirmed_registrations = count_confirmed_event_registrations(organizacao)
        eventos_por_nucleo = calculate_events_by_nucleo(organizacao)
        eventos_chart = build_chart_payload(event_totals)
        membros_chart = build_chart_payload(membership_totals)
        eventos_por_nucleo_chart = build_chart_payload(
            eventos_por_nucleo, chart_type="bar"
        )

        monthly_membros = calculate_monthly_membros(organizacao, months=months)
        monthly_nucleados = calculate_monthly_nucleados(organizacao, months=months)
        monthly_registrations = calculate_monthly_event_registrations(
            organizacao, months=months
        )
        monthly_registration_values = calculate_monthly_registration_values(
            organizacao, months=months
        )

        membros_por_periodo_chart = build_time_series_chart(
            monthly_membros,
            value_field="total",
            std_field="std_dev",
            label=_("Membros"),
            color="#2563eb",
            value_format=".0f",
        )
        nucleados_por_periodo_chart = build_time_series_chart(
            monthly_nucleados,
            value_field="total",
            std_field="std_dev",
            label=_("Nucleados"),
            color="#0ea5e9",
            value_format=".0f",
        )
        inscricoes_por_periodo_chart = build_time_series_chart(
            monthly_registrations,
            value_field="total",
            label=_("Inscrições confirmadas"),
            color="#7c3aed",
            value_format=".0f",
        )
        valores_inscricoes_por_periodo_chart = build_time_series_chart(
            monthly_registration_values,
            value_field="total",
            std_field="std_dev",
            label=_("Valor total das inscrições"),
            color="#22c55e",
            value_format=".2f",
            value_prefix="R$ ",
            yaxis_tickprefix="R$ ",
        )

        context.update(
            {
                "total_membros": sum(membership_totals.values()),
                "total_nucleados": membership_totals.get(
                    MEMBROS_NUCLEADOS_LABEL, 0
                ),
                "inscricoes_confirmadas": confirmed_registrations,
                "eventos_por_status": event_totals,
                "eventos_ativos": event_totals.get(Evento.Status.ATIVO.label, 0),
                "eventos_concluidos": event_totals.get(Evento.Status.CONCLUIDO.label, 0),
                "eventos_planejamento": event_totals.get(Evento.Status.PLANEJAMENTO.label, 0),
                "eventos_chart": eventos_chart,
                "eventos_por_nucleo": eventos_por_nucleo_chart,
                "membros_chart": membros_chart,
                "membros_por_periodo_chart": membros_por_periodo_chart,
                "nucleados_por_periodo_chart": nucleados_por_periodo_chart,
                "inscricoes_por_periodo_chart": inscricoes_por_periodo_chart,
                "valores_inscricoes_por_periodo_chart": valores_inscricoes_por_periodo_chart,
                "total_eventos": eventos_chart.get("total", 0),
                "dashboard_period_months": months,
                "dashboard_period_choices": self.PERIOD_CHOICES,
                "dashboard_period_changed": "months" in self.request.GET,
            }
        )
        return context


class MembroDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard direcionado a membros que não são coordenadores."""

    template_name = "dashboard/membro_dashboard.html"
    CONNECTION_LIMIT = 6
    FAVORITES_LIMIT = 6
    EVENT_LIMIT = 6

    def dispatch(self, request, *args, **kwargs):
        allowed_roles = {
            UserType.ASSOCIADO.value,
            UserType.NUCLEADO.value,
        }
        if request.user.get_tipo_usuario not in allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        avaliacao_stats = FeedbackNota.objects.filter(usuario=user).aggregate(
            media=Avg("nota"), total=Count("id")
        )
        avaliacao_media = avaliacao_stats["media"]
        avaliacao_display = (
            f"{avaliacao_media:.1f}" if avaliacao_media is not None else ""
        )

        total_conexoes = user.connections.count() if hasattr(user, "connections") else 0
        conexoes = list(
            user.connections.select_related("organizacao")
            .order_by("nome_fantasia", "contato", "username")[: self.CONNECTION_LIMIT]
        )
        conexoes_restantes = max(total_conexoes - len(conexoes), 0)

        total_posts = user.posts.filter(deleted=False).count()
        total_reacoes = user.reacoes.filter(deleted=False).count()

        participacoes = list(
            user.participacoes.select_related("nucleo")
            .filter(status="ativo", status_suspensao=False, papel="membro")
            .order_by("nucleo__nome")
        )

        now = timezone.now()
        inscricoes_qs = (
            InscricaoEvento.objects.filter(user=user)
            .filter(Q(status__in=["confirmada", "pendente"]) | Q(presente=True))
            .filter(evento__status__in=[Evento.Status.ATIVO, Evento.Status.PLANEJAMENTO])
            .filter(evento__data_fim__gte=now)
            .select_related("evento")
            .order_by("-evento__data_inicio", "-created_at")
        )
        inscricoes_ativas = list(inscricoes_qs[: self.EVENT_LIMIT])
        for inscricao in inscricoes_ativas:
            valor_exibicao = inscricao.valor_pago
            if valor_exibicao is None:
                valor_exibicao = inscricao.get_valor_evento()
            inscricao.valor_exibicao = valor_exibicao

        favoritos = list(
            Bookmark.objects.filter(user=user, post__isnull=False)
            .select_related("post", "post__autor")
            .order_by("-created_at")[: self.FAVORITES_LIMIT]
        )

        context.update(
            {
                "avaliacao_media": avaliacao_media,
                "avaliacao_display": avaliacao_display,
                "avaliacao_total": avaliacao_stats["total"],
                "total_conexoes": total_conexoes,
                "conexoes": conexoes,
                "conexoes_restantes": conexoes_restantes,
                "total_posts": total_posts,
                "total_reacoes": total_reacoes,
                "participacoes": participacoes,
                "inscricoes_ativas": inscricoes_ativas,
                "favoritos": favoritos,
            }
        )
        return context


class RoleDashboardMixin(LoginRequiredMixin):
    """Compartilha utilitários entre dashboards segmentados por perfil."""

    DEFAULT_MONTHS = 12
    PERIOD_CHOICES: tuple[int, ...] = (3, 6, 12, 24)
    role_type: UserType | None = None

    def dispatch(self, request, *args, **kwargs):
        tipo = getattr(request.user, "get_tipo_usuario", None)
        if not self.role_type or tipo != self.role_type.value:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def _resolve_months(self) -> int:
        raw_months = self.request.GET.get("months")
        if not raw_months:
            return self.DEFAULT_MONTHS
        try:
            months = int(raw_months)
        except (TypeError, ValueError):
            return self.DEFAULT_MONTHS
        if months not in self.PERIOD_CHOICES:
            return self.DEFAULT_MONTHS
        return months

    def _format_currency(self, value: Decimal | None) -> str:
        normalized = value or Decimal("0")
        formatted = number_format(normalized, decimal_pos=2, force_grouping=True)
        return f"R$ {formatted}"

    def _build_events_vs_registrations_chart(
        self,
        monthly_events: list[dict[str, Any]],
        monthly_registrations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        events_chart = build_time_series_chart(
            monthly_events,
            value_field="total",
            label=_("Eventos"),
            color="#0ea5e9",
            value_format=".0f",
        )
        registrations_chart = build_time_series_chart(
            monthly_registrations,
            value_field="total",
            label=_("Inscrições confirmadas"),
            color="#7c3aed",
            value_format=".0f",
        )

        combined_points: list[dict[str, Any]] = []
        for event_point, registration_point in zip_longest(
            monthly_events, monthly_registrations, fillvalue={}
        ):
            period = event_point.get("period") or registration_point.get("period")
            combined_points.append(
                {
                    "period": period,
                    "eventos": event_point.get("total", 0),
                    "inscricoes": registration_point.get("total", 0),
                }
            )

        figure = deepcopy(events_chart.get("figure", {}))
        figure.setdefault("data", [])
        figure["data"].extend(
            deepcopy(registrations_chart.get("figure", {}).get("data", []))
        )
        figure.setdefault("layout", {})
        figure["layout"].setdefault("legend", {})
        figure["layout"]["legend"].update(
            {"orientation": "h", "y": -0.18, "x": 0.5, "xanchor": "center"}
        )

        return {"points": combined_points, "figure": figure, "type": "line"}

    def _serialize_chart(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload.get("figure", {}), cls=DjangoJSONEncoder)


class CoordenadorDashboardView(RoleDashboardMixin, TemplateView):
    """Dashboard específico para usuários coordenadores."""

    template_name = "dashboard/coordenadores_dashboard.html"
    role_type = UserType.COORDENADOR
    EVENT_LIST_LIMIT = 6

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        organizacao = getattr(user, "organizacao", None)
        months = self._resolve_months()

        nucleos_qs = (
            Nucleo.objects.filter(
                participacoes__user=user,
                participacoes__papel="coordenador",
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            )
            .annotate(
                total_membros=Count(
                    "participacoes",
                    filter=Q(
                        participacoes__status="ativo",
                        participacoes__status_suspensao=False,
                    ),
                    distinct=True,
                )
            )
            .order_by("nome")
            .distinct()
        )
        nucleos = list(nucleos_qs)
        nucleo_ids = [nucleo.id for nucleo in nucleos if nucleo.id]

        eventos_base_qs = (
            Evento.objects.filter(
                organizacao=organizacao,
                nucleo_id__in=nucleo_ids,
            )
            if nucleo_ids
            else Evento.objects.none()
        )
        eventos_list = (
            eventos_base_qs.filter(
                status__in=[Evento.Status.ATIVO, Evento.Status.PLANEJAMENTO]
            )
            .select_related("nucleo")
            .annotate(
                total_inscritos=Count(
                    "inscricoes",
                    filter=Q(inscricoes__status="confirmada"),
                    distinct=True,
                ),
                valor_total_inscricoes=Sum(
                    "inscricoes__valor_pago",
                    filter=Q(inscricoes__status="confirmada"),
                ),
            )
            .order_by("-data_inicio")[: self.EVENT_LIST_LIMIT]
            if nucleo_ids
            else []
        )

        inscricoes_qs = (
            InscricaoEvento.objects.filter(
                evento__organizacao=organizacao,
                evento__nucleo_id__in=nucleo_ids,
                status="confirmada",
            )
            if nucleo_ids
            else InscricaoEvento.objects.none()
        )
        total_inscritos = inscricoes_qs.count()
        valor_total_inscricoes = inscricoes_qs.aggregate(total=Sum("valor_pago"))["total"]

        monthly_kwargs = {"months": months, "nucleo_ids": nucleo_ids}
        monthly_events = calculate_monthly_events(
            organizacao,
            statuses=[Evento.Status.ATIVO, Evento.Status.PLANEJAMENTO],
            **monthly_kwargs,
        )
        monthly_registrations = calculate_monthly_event_registrations(
            organizacao, **monthly_kwargs
        )
        monthly_nucleados = calculate_monthly_nucleados(organizacao, **monthly_kwargs)
        monthly_registration_values = calculate_monthly_registration_values(
            organizacao, **monthly_kwargs
        )

        eventos_inscricoes_chart = self._build_events_vs_registrations_chart(
            monthly_events, monthly_registrations
        )
        nucleados_chart = build_time_series_chart(
            monthly_nucleados,
            value_field="total",
            std_field="std_dev",
            label=_("Nucleados ativos"),
            color="#0ea5e9",
            value_format=".0f",
        )
        valores_chart = build_time_series_chart(
            monthly_registration_values,
            value_field="total",
            std_field="std_dev",
            label=_("Receita das inscrições"),
            color="#22c55e",
            value_format=".2f",
            value_prefix="R$ ",
            yaxis_tickprefix="R$ ",
        )

        context.update(
            {
                "nucleos_coordenados": nucleos,
                "eventos_coordenados": list(eventos_list),
                "total_nucleos": len(nucleos),
                "total_eventos": eventos_base_qs.filter(
                    status=Evento.Status.ATIVO
                ).count()
                if nucleo_ids
                else 0,
                "total_inscritos": total_inscritos,
                "valor_total_inscricoes": self._format_currency(valor_total_inscricoes),
                "eventos_inscricoes_por_periodo_chart": eventos_inscricoes_chart,
                "nucleados_por_periodo_chart": nucleados_chart,
                "valores_inscricoes_por_periodo_chart": valores_chart,
                "dashboard_period_months": months,
                "dashboard_period_choices": self.PERIOD_CHOICES,
                "dashboard_period_changed": "months" in self.request.GET,
            }
        )
        return context


class ConsultorDashboardView(RoleDashboardMixin, TemplateView):
    """Dashboard para consultores de núcleos."""

    template_name = "dashboard/consultor_dashboard.html"
    role_type = UserType.CONSULTOR
    EVENT_LIST_LIMIT = 6

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        organizacao = getattr(user, "organizacao", None)
        months = self._resolve_months()

        nucleos_qs = (
            Nucleo.objects.filter(consultor=user)
            .annotate(
                total_membros=Count(
                    "participacoes",
                    filter=Q(
                        participacoes__status="ativo",
                        participacoes__status_suspensao=False,
                    ),
                    distinct=True,
                )
            )
            .order_by("nome")
        )
        nucleos = list(nucleos_qs)
        nucleo_ids = [nucleo.id for nucleo in nucleos if nucleo.id]

        eventos_base_qs = (
            Evento.objects.filter(
                organizacao=organizacao,
                nucleo_id__in=nucleo_ids,
            )
            if nucleo_ids
            else Evento.objects.none()
        )
        eventos_list = (
            eventos_base_qs.filter(
                status__in=[Evento.Status.ATIVO, Evento.Status.PLANEJAMENTO]
            )
            .select_related("nucleo")
            .annotate(
                total_inscritos=Count(
                    "inscricoes",
                    filter=Q(inscricoes__status="confirmada"),
                    distinct=True,
                ),
                valor_total_inscricoes=Sum(
                    "inscricoes__valor_pago",
                    filter=Q(inscricoes__status="confirmada"),
                ),
            )
            .order_by("-data_inicio")[: self.EVENT_LIST_LIMIT]
            if nucleo_ids
            else []
        )

        inscricoes_qs = (
            InscricaoEvento.objects.filter(
                evento__organizacao=organizacao,
                evento__nucleo_id__in=nucleo_ids,
                status="confirmada",
            )
            if nucleo_ids
            else InscricaoEvento.objects.none()
        )
        total_inscritos = inscricoes_qs.count()
        valor_total_inscricoes = inscricoes_qs.aggregate(total=Sum("valor_pago"))["total"]

        monthly_kwargs = {"months": months, "nucleo_ids": nucleo_ids}
        monthly_events = calculate_monthly_events(
            organizacao,
            statuses=[Evento.Status.ATIVO, Evento.Status.PLANEJAMENTO],
            **monthly_kwargs,
        )
        monthly_registrations = calculate_monthly_event_registrations(
            organizacao, **monthly_kwargs
        )
        monthly_nucleados = calculate_monthly_nucleados(organizacao, **monthly_kwargs)
        monthly_registration_values = calculate_monthly_registration_values(
            organizacao, **monthly_kwargs
        )

        eventos_inscricoes_chart = self._build_events_vs_registrations_chart(
            monthly_events, monthly_registrations
        )
        nucleados_chart = build_time_series_chart(
            monthly_nucleados,
            value_field="total",
            std_field="std_dev",
            label=_("Nucleados ativos"),
            color="#0ea5e9",
            value_format=".0f",
        )
        valores_chart = build_time_series_chart(
            monthly_registration_values,
            value_field="total",
            std_field="std_dev",
            label=_("Receita das inscrições"),
            color="#22c55e",
            value_format=".2f",
            value_prefix="R$ ",
            yaxis_tickprefix="R$ ",
        )

        context.update(
            {
                "nucleos_consultoria": nucleos,
                "eventos_consultoria": list(eventos_list),
                "total_nucleos_consultoria": len(nucleos),
                "total_eventos_consultoria": eventos_base_qs.filter(
                    status=Evento.Status.ATIVO
                ).count()
                if nucleo_ids
                else 0,
                "total_inscritos_consultoria": total_inscritos,
                "valor_total_inscricoes_consultoria": self._format_currency(
                    valor_total_inscricoes
                ),
                "eventos_inscricoes_chart": eventos_inscricoes_chart,
                "nucleados_chart": nucleados_chart,
                "receita_inscricoes_chart": valores_chart,
                "dashboard_period_months": months,
                "dashboard_period_choices": self.PERIOD_CHOICES,
                "dashboard_period_changed": "months" in self.request.GET,
            }
        )
        return context


class DashboardRouterView(LoginRequiredMixin, View):
    """Direciona o usuário para o dashboard apropriado conforme o perfil."""

    def dispatch(self, request, *args, **kwargs):
        tipo = getattr(request.user, "get_tipo_usuario", None)
        if tipo in {
            UserType.ROOT.value,
            UserType.ADMIN.value,
            UserType.OPERADOR.value,
        }:
            return AdminDashboardView.as_view()(request, *args, **kwargs)
        if tipo == UserType.COORDENADOR.value:
            return CoordenadorDashboardView.as_view()(request, *args, **kwargs)
        if tipo in {UserType.ASSOCIADO.value, UserType.NUCLEADO.value}:
            return MembroDashboardView.as_view()(request, *args, **kwargs)
        if tipo == UserType.CONSULTOR.value:
            return ConsultorDashboardView.as_view()(request, *args, **kwargs)
        raise PermissionDenied
