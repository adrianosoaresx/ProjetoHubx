from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from accounts.models import UserType
from agenda.models import Evento
from core.permissions import (
    AdminRequiredMixin,
    ClienteRequiredMixin,
    GerenteRequiredMixin,
    SuperadminRequiredMixin,
)
from empresas.models import Empresa
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .services import DashboardService

User = get_user_model()


class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """Base view para calcular métricas."""

    def get_metrics(self):
        periodo = self.request.GET.get("periodo", "mensal")
        inicio_str = self.request.GET.get("inicio")
        fim_str = self.request.GET.get("fim")
        inicio = datetime.fromisoformat(inicio_str) if inicio_str else None
        fim = datetime.fromisoformat(fim_str) if fim_str else None
        inicio, fim = DashboardService.get_period_range(periodo, inicio, fim)

        qs_users = User.objects.all()
        qs_orgs = Organizacao.objects.all()
        qs_nucleos = Nucleo.objects.all()
        qs_empresas = Empresa.objects.all()
        qs_eventos = Evento.objects.all()

        user = self.request.user
        if user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            org = user.organizacao

            qs_users = qs_users.filter(organizacao=org)
            qs_orgs = qs_orgs.filter(pk=getattr(org, "pk", None))
            qs_nucleos = qs_nucleos.filter(organizacao=org)
            qs_empresas = qs_empresas.filter(usuario__organizacao=org)
            qs_eventos = qs_eventos.filter(organizacao=org)

        return {
            "num_users": DashboardService.calcular_crescimento(qs_users, inicio, fim),
            "num_organizacoes": DashboardService.calcular_crescimento(qs_orgs, inicio, fim),
            "num_nucleos": DashboardService.calcular_crescimento(qs_nucleos, inicio, fim),
            "num_empresas": DashboardService.calcular_crescimento(qs_empresas, inicio, fim),
            "num_eventos": DashboardService.calcular_crescimento(qs_eventos, inicio, fim),
        }

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
