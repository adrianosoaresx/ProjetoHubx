from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.permissions import (
    SuperadminRequiredMixin,
    AdminRequiredMixin,
    GerenteRequiredMixin,
    ClienteRequiredMixin,
)
from organizacoes.models import Organizacao
from nucleos.models import Nucleo
from empresas.models import Empresa
from eventos.models import Evento

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
            org = user.organizacao
            qs_users = qs_users.filter(organizacao=org)
            qs_orgs = qs_orgs.filter(pk=getattr(org, "pk", None))
            qs_nucleos = qs_nucleos.filter(organizacao=org)
            qs_empresas = qs_empresas.filter(usuario__organizacao=org)
            qs_eventos = qs_eventos.filter(organizacao=org)

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
