from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.views.generic import TemplateView

from accounts.models import UserType
from core.permissions import (
    AdminRequiredMixin,
    ClienteRequiredMixin,
    GerenteRequiredMixin,
    SuperadminRequiredMixin,
)

from .services import DashboardMetricsService, DashboardService

User = get_user_model()


class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """Base view para calcular métricas."""

    def get_metrics(self):
        periodo = self.request.GET.get("periodo", "mensal")
        inicio_str = self.request.GET.get("inicio")
        fim_str = self.request.GET.get("fim")
        inicio = datetime.fromisoformat(inicio_str) if inicio_str else None
        fim = datetime.fromisoformat(fim_str) if fim_str else None
        return DashboardMetricsService.get_metrics(self.request.user, periodo, inicio, fim)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_metrics())
        return context


class RootDashboardView(SuperadminRequiredMixin, DashboardBaseView):
    template_name = "dashboard/root.html"


class AdminDashboardView(AdminRequiredMixin, DashboardBaseView):
    template_name = "dashboard/admin.html"


class GerenteDashboardView(GerenteRequiredMixin, DashboardBaseView):
    template_name = "dashboard/gerente.html"


class ClienteDashboardView(ClienteRequiredMixin, DashboardBaseView):
    template_name = "dashboard/cliente.html"


def dashboard_redirect(request):
    """Redireciona usuário para o dashboard apropriado."""
    user = request.user
    if not user.is_authenticated:
        return redirect("accounts:login")

    if user.user_type == UserType.ROOT:
        return redirect("dashboard:root")
    if user.user_type == UserType.ADMIN:
        return redirect("dashboard:admin")
    if user.user_type == UserType.COORDENADOR:
        return redirect("dashboard:gerente")
    return redirect("dashboard:cliente")


def metrics_partial(request):
    """Retorna HTML com métricas para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    metrics = DashboardMetricsService.get_metrics(request.user)
    html = render_to_string(
        "dashboard/partials/metrics_list.html",
        metrics,
        request=request,
    )
    return HttpResponse(html)


def lancamentos_partial(request):
    """Últimos lançamentos financeiros."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    lancamentos = DashboardService.ultimos_lancamentos(request.user)
    html = render_to_string(
        "dashboard/partials/latest_transactions.html",
        {"lancamentos": lancamentos},
        request=request,
    )
    return HttpResponse(html)
