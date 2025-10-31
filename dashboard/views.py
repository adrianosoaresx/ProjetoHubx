from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.permissions import AdminRequiredMixin

from eventos.models import Evento

from .services import (
    build_chart_payload,
    calculate_event_status_totals,
    calculate_events_by_nucleo,
    calculate_membership_totals,
    count_confirmed_event_registrations,
)


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """View principal do painel administrativo."""

    template_name = "dashboard/admin_dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        organizacao = getattr(self.request.user, "organizacao", None)

        membership_totals = calculate_membership_totals(organizacao)
        event_totals = calculate_event_status_totals(organizacao)
        confirmed_registrations = count_confirmed_event_registrations(organizacao)
        eventos_por_nucleo = calculate_events_by_nucleo(organizacao)
        eventos_chart = build_chart_payload(event_totals)
        membros_chart = build_chart_payload(membership_totals)
        eventos_por_nucleo_chart = build_chart_payload(eventos_por_nucleo)

        context.update(
            {
                "total_associados": membership_totals.get("Associados", 0),
                "total_nucleados": membership_totals.get("Nucleados", 0),
                "inscricoes_confirmadas": confirmed_registrations,
                "eventos_por_status": event_totals,
                "eventos_ativos": event_totals.get(Evento.Status.ATIVO.label, 0),
                "eventos_concluidos": event_totals.get(Evento.Status.CONCLUIDO.label, 0),
                "eventos_planejamento": event_totals.get(Evento.Status.PLANEJAMENTO.label, 0),
                "eventos_chart": eventos_chart,
                "eventos_por_nucleo": eventos_por_nucleo_chart,
                "membros_chart": membros_chart,
                "total_eventos": eventos_chart.get("total", 0),
            }
        )
        return context
