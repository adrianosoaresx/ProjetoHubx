import csv
import shutil
from datetime import datetime
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, TemplateView, View

from accounts.models import UserType
from core.permissions import (
    AdminRequiredMixin,
    ClienteRequiredMixin,
    GerenteRequiredMixin,
    SuperadminRequiredMixin,
)

from .forms import DashboardConfigForm
from .models import DashboardConfig
from .services import DashboardMetricsService, DashboardService

User = get_user_model()


class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """Base view para calcular métricas."""

    def get_metrics(self):
        periodo = self.request.GET.get("periodo", "mensal")
        escopo = self.request.GET.get("escopo", "auto")
        inicio_str = self.request.GET.get("inicio")
        fim_str = self.request.GET.get("fim")
        inicio = datetime.fromisoformat(inicio_str) if inicio_str else None
        fim = datetime.fromisoformat(fim_str) if fim_str else None
        filters: dict[str, object] = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            value = self.request.GET.get(key)
            if value:
                filters[key] = value
        metricas_param = self.request.GET.get("metricas")
        if metricas_param:
            filters["metricas"] = [m for m in metricas_param.split(",") if m]

        self.periodo = periodo
        self.escopo = escopo
        self.filters = filters
        return DashboardMetricsService.get_metrics(
            self.request.user,
            periodo=periodo,
            inicio=inicio,
            fim=fim,
            escopo=escopo,
            **filters,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metrics = self.get_metrics()
        context.update(metrics)
        context["periodo"] = getattr(self, "periodo", "mensal")
        context["escopo"] = getattr(self, "escopo", "auto")
        context["filtros"] = getattr(self, "filters", {})
        metricas = self.filters.get("metricas") if hasattr(self, "filters") else None
        metricas = metricas or ["num_users", "num_eventos", "num_posts"]
        context["metricas_selecionadas"] = metricas
        context["chart_data"] = [metrics[m]["total"] for m in metricas if m in metrics]
        return context


class RootDashboardView(SuperadminRequiredMixin, DashboardBaseView):
    template_name = "dashboard/root.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total, used, _free = shutil.disk_usage("/")
        context["service_status"] = {
            "celery": _("Desconhecido"),
            "fila_mensagens": 0,
            "disco": round(used / total * 100, 2),
        }
        context["security_metrics"] = {"login_bloqueados": 0}
        return context


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
    try:
        metrics = DashboardMetricsService.get_metrics(request.user)
        html = render_to_string(
            "dashboard/partials/metrics_list.html",
            metrics,
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover - logado
        messages.error(request, _("Erro ao carregar métricas."))
        return HttpResponse(status=500)


def lancamentos_partial(request):
    """Últimos lançamentos financeiros."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    try:
        lancamentos = DashboardService.ultimos_lancamentos(request.user)
        html = render_to_string(
            "dashboard/partials/latest_transactions.html",
            {"lancamentos": lancamentos},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover - logado
        messages.error(request, _("Erro ao carregar lançamentos."))
        return HttpResponse(status=500)


def notificacoes_partial(request):
    """Notificações recentes para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    try:
        notificacoes = DashboardService.ultimas_notificacoes(request.user)
        html = render_to_string(
            "dashboard/partials/notifications_list.html",
            {"notificacoes": notificacoes},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover
        messages.error(request, _("Erro ao carregar notificações."))
        return HttpResponse(status=500)


def tarefas_partial(request):
    """Tarefas pendentes para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    try:
        tarefas = DashboardService.tarefas_pendentes(request.user)
        html = render_to_string(
            "dashboard/partials/pending_tasks.html",
            {"tarefas": tarefas},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover
        messages.error(request, _("Erro ao carregar tarefas."))
        return HttpResponse(status=500)


def eventos_partial(request):
    """Próximos eventos para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    try:
        eventos = DashboardService.proximos_eventos(request.user)
        html = render_to_string(
            "dashboard/partials/upcoming_events.html",
            {"eventos": eventos},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover
        messages.error(request, _("Erro ao carregar eventos."))
        return HttpResponse(status=500)


class DashboardExportView(LoginRequiredMixin, View):
    """Exporta métricas em CSV ou PDF."""

    def get(self, request):
        user = request.user
        if user.user_type not in {UserType.ROOT, UserType.ADMIN, UserType.COORDENADOR}:
            return HttpResponse(status=403)

        periodo = request.GET.get("periodo", "mensal")
        escopo = request.GET.get("escopo", "auto")
        formato = request.GET.get("formato", "csv")

        filters: dict[str, object] = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id", "metricas"]:
            value = request.GET.get(key)
            if value:
                if key == "metricas":
                    filters[key] = [m for m in value.split(",") if m]
                else:
                    filters[key] = value

        metrics = DashboardMetricsService.get_metrics(
            user,
            periodo=periodo,
            escopo=escopo,
            **filters,
        )

        if formato == "pdf":
            try:
                from reportlab.pdfgen import canvas
            except Exception:
                return HttpResponse(status=500)
            buffer = BytesIO()
            p = canvas.Canvas(buffer)
            y = 800
            p.drawString(50, y, "Métricas do Dashboard")
            y -= 30
            for key, data in metrics.items():
                p.drawString(
                    50,
                    y,
                    f"{key}: total={data['total']} crescimento={data['crescimento']:.2f}%",
                )
                y -= 20
            p.showPage()
            p.save()
            buffer.seek(0)
            resp = HttpResponse(buffer.getvalue(), content_type="application/pdf")
            filename = datetime.now().strftime("metrics_%Y%m%d_%H%M%S.pdf")
            resp["Content-Disposition"] = f"attachment; filename={filename}"
            return resp

        # default csv
        resp = HttpResponse(content_type="text/csv")
        filename = datetime.now().strftime("metrics_%Y%m%d_%H%M%S.csv")
        resp["Content-Disposition"] = f"attachment; filename={filename}"
        writer = csv.writer(resp)
        writer.writerow(["metric", "total", "crescimento"])
        for key, data in metrics.items():
            writer.writerow([key, data["total"], data["crescimento"]])
        return resp


class DashboardConfigCreateView(LoginRequiredMixin, CreateView):
    form_class = DashboardConfigForm
    template_name = "dashboard/config_form.html"

    def get_success_url(self):
        return reverse("dashboard:configs")

    def form_valid(self, form):
        config_data = {
            "periodo": self.request.GET.get("periodo", "mensal"),
            "escopo": self.request.GET.get("escopo", "auto"),
            "filters": {},
        }
        for key in ["organizacao_id", "nucleo_id", "evento_id", "metricas"]:
            val = self.request.GET.get(key)
            if val:
                if key == "metricas":
                    config_data["filters"][key] = [m for m in val.split(",") if m]
                else:
                    config_data["filters"][key] = val
        form.save(self.request.user, config_data)
        return super().form_valid(form)


class DashboardConfigListView(LoginRequiredMixin, ListView):
    model = DashboardConfig
    template_name = "dashboard/config_list.html"

    def get_queryset(self):
        qs = DashboardConfig.objects.filter(user=self.request.user)
        if self.request.user.user_type in {UserType.ROOT, UserType.ADMIN}:
            qs = qs | DashboardConfig.objects.filter(publico=True).exclude(user=self.request.user)
        return qs


class DashboardConfigApplyView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cfg = DashboardConfig.objects.filter(pk=pk).first()
        if not cfg or (cfg.user != request.user and not cfg.publico):
            return HttpResponse(status=403)
        params = cfg.config.copy()
        filters = params.pop("filters", {})
        params.update(filters)
        url = reverse("dashboard:dashboard") + "?" + "&".join(
            f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in params.items()
        )
        return redirect(url)
