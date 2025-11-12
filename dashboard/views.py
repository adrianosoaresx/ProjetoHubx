from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from core.permissions import AdminOrOperatorRequiredMixin

from eventos.models import Evento

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
            }
        )
        return context
