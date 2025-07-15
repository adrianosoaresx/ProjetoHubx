from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

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

User = get_user_model()


class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """Base view para calcular métricas."""

    def get_metrics(self):
        qs_users = User.objects.all()
        qs_orgs = Organizacao.objects.all()
        qs_nucleos = Nucleo.objects.all()
        qs_empresas = Empresa.objects.all()
        qs_eventos = Evento.objects.all()

        user = self.request.user
        if user.tipo_id in {User.Tipo.ADMIN, User.Tipo.GERENTE}:
            org = user.organizacao  # <- correto no User

            qs_users = qs_users.filter(organizacao=org)
            qs_orgs = qs_orgs.filter(pk=getattr(org, "pk", None))
            qs_nucleos = qs_nucleos.filter(organizacao=org)  # Corrigido para usar 'organizacao'
            qs_empresas = qs_empresas.filter(usuario__organizacao=org)
            qs_eventos = qs_eventos.filter(organizacao=org)  # Corrigido para usar 'organizacao'

        return {
            "num_users": qs_users.count(),
            "num_organizacoes": qs_orgs.count(),
            "num_nucleos": qs_nucleos.count(),
            "num_empresas": qs_empresas.count(),
            "num_eventos": qs_eventos.count(),
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

    if user.tipo_id == User.Tipo.SUPERADMIN:
        return redirect("dashboard:root")
    if user.tipo_id == User.Tipo.ADMIN:
        return redirect("dashboard:admin")
    if user.tipo_id == User.Tipo.GERENTE:
        return redirect("dashboard:gerente")
    return redirect("dashboard:cliente")
