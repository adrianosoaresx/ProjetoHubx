from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from core.permissions import AdminOrOperatorRequiredMixin

from eventos.models import Evento
from eventos.models import FeedbackNota, InscricaoEvento

from accounts.models import UserType
from feed.models import Bookmark

from .services import (
    ASSOCIADOS_NUCLEADOS_LABEL,
    build_chart_payload,
    build_time_series_chart,
    calculate_event_status_totals,
    calculate_events_by_nucleo,
    calculate_membership_totals,
    calculate_monthly_associates,
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
        eventos_por_nucleo_chart = build_chart_payload(eventos_por_nucleo)

        monthly_associates = calculate_monthly_associates(organizacao, months=months)
        monthly_nucleados = calculate_monthly_nucleados(organizacao, months=months)
        monthly_registrations = calculate_monthly_event_registrations(
            organizacao, months=months
        )
        monthly_registration_values = calculate_monthly_registration_values(
            organizacao, months=months
        )

        associados_por_periodo_chart = build_time_series_chart(
            monthly_associates,
            value_field="total",
            std_field="std_dev",
            label=_("Associados"),
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
                "total_associados": sum(membership_totals.values()),
                "total_nucleados": membership_totals.get(
                    ASSOCIADOS_NUCLEADOS_LABEL, 0
                ),
                "inscricoes_confirmadas": confirmed_registrations,
                "eventos_por_status": event_totals,
                "eventos_ativos": event_totals.get(Evento.Status.ATIVO.label, 0),
                "eventos_concluidos": event_totals.get(Evento.Status.CONCLUIDO.label, 0),
                "eventos_planejamento": event_totals.get(Evento.Status.PLANEJAMENTO.label, 0),
                "eventos_chart": eventos_chart,
                "eventos_por_nucleo": eventos_por_nucleo_chart,
                "membros_chart": membros_chart,
                "associados_por_periodo_chart": associados_por_periodo_chart,
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


class AssociadoDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard direcionado a associados que não são coordenadores."""

    template_name = "dashboard/associado_dashboard.html"
    CONNECTION_LIMIT = 6
    PORTFOLIO_LIMIT = 6
    FAVORITES_LIMIT = 6
    EVENT_LIMIT = 6

    def dispatch(self, request, *args, **kwargs):
        if request.user.get_tipo_usuario != UserType.ASSOCIADO.value:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user

        avaliacao_stats = FeedbackNota.objects.filter(usuario=user).aggregate(
            media=Avg("nota"), total=Count("id")
        )
        avaliacao_media = avaliacao_stats["media"]
        avaliacao_display = f"{avaliacao_media:.1f}" if avaliacao_media is not None else _("Sem dados")

        total_conexoes = user.connections.count() if hasattr(user, "connections") else 0
        conexoes = list(
            user.connections.select_related("organizacao")
            .order_by("first_name", "username")[: self.CONNECTION_LIMIT]
        )
        conexoes_restantes = max(total_conexoes - len(conexoes), 0)

        total_posts = user.posts.filter(deleted=False).count()
        total_reacoes = user.reacoes.filter(deleted=False).count()

        participacoes = list(
            user.participacoes.select_related("nucleo")
            .filter(status="ativo", status_suspensao=False, papel="membro")
            .order_by("nucleo__nome")
        )

        eventos = list(
            InscricaoEvento.objects.filter(user=user)
            .filter(Q(status__in=["confirmada", "pendente"]) | Q(presente=True))
            .select_related("evento")
            .order_by("-evento__data_inicio", "-created_at")[: self.EVENT_LIMIT]
        )

        destaques_qs = (
            user.medias.filter(publico=True, tags__nome__iexact="destaque")
            .prefetch_related("tags")
            .order_by("-created_at")
            .distinct()
        )
        destaques = list(destaques_qs[: self.PORTFOLIO_LIMIT])
        if not destaques:
            destaques = list(
                user.medias.filter(publico=True)
                .prefetch_related("tags")
                .order_by("-created_at")[: self.PORTFOLIO_LIMIT]
            )

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
                "eventos": eventos,
                "portfolio_destaques": destaques,
                "favoritos": favoritos,
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
        if tipo == UserType.ASSOCIADO.value:
            return AssociadoDashboardView.as_view()(request, *args, **kwargs)
        raise PermissionDenied
