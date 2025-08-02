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

        inicio_str = self.request.GET.get("data_inicio")
        fim_str = self.request.GET.get("data_fim")
        inicio = datetime.fromisoformat(inicio_str) if inicio_str else None
        fim = datetime.fromisoformat(fim_str) if fim_str else None

        filters: dict[str, object] = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            value = self.request.GET.get(key)
            if value:
                filters[key] = value

        metricas_list = self.request.GET.getlist("metricas")
        if metricas_list:
            filters["metricas"] = metricas_list

        self.periodo = periodo
        self.escopo = escopo
        self.filters = {**filters, "data_inicio": inicio_str, "data_fim": fim_str}

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
        context["metrics_data"] = metrics
        context["periodo"] = getattr(self, "periodo", "mensal")
        context["escopo"] = getattr(self, "escopo", "auto")
        context["filtros"] = getattr(self, "filters", {})
        metricas = self.filters.get("metricas") if hasattr(self, "filters") else None
        metricas = metricas or ["num_users", "num_eventos", "num_posts"]
        context["metricas_selecionadas"] = metricas
        context["chart_data"] = [metrics[m]["total"] for m in metricas if m in metrics]
        metricas_info = {
            "num_users": {"label": _("Usuários"), "icon": "fa-users"},
            "num_organizacoes": {"label": _("Organizações"), "icon": "fa-building"},
            "num_nucleos": {"label": _("Núcleos"), "icon": "fa-users-rectangle"},
            "num_empresas": {"label": _("Empresas"), "icon": "fa-city"},
            "num_eventos": {"label": _("Eventos"), "icon": "fa-calendar"},
            "num_posts": {"label": _("Posts"), "icon": "fa-newspaper"},
        }
        context["metricas_disponiveis"] = [
            {"key": key, "label": data["label"]} for key, data in metricas_info.items()
        ]
        context["metrics_iter"] = [
            {"key": m, "data": metrics[m], "label": metricas_info[m]["label"], "icon": metricas_info[m]["icon"]}
            for m in metricas
            if m in metrics
        ]
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
        metricas = request.GET.getlist("metricas") or [
            "num_users",
            "num_organizacoes",
            "num_nucleos",
            "num_empresas",
            "num_eventos",
            "num_posts",
        ]
        metrics = DashboardMetricsService.get_metrics(
            request.user, metricas=metricas
        )
        info = {
            "num_users": {"label": _("Usuários"), "icon": "fa-users"},
            "num_organizacoes": {"label": _("Organizações"), "icon": "fa-building"},
            "num_nucleos": {"label": _("Núcleos"), "icon": "fa-users-rectangle"},
            "num_empresas": {"label": _("Empresas"), "icon": "fa-city"},
            "num_eventos": {"label": _("Eventos"), "icon": "fa-calendar"},
            "num_posts": {"label": _("Posts"), "icon": "fa-newspaper"},
        }
        metrics_iter = [
            {"key": m, "data": metrics[m], "label": info[m]["label"], "icon": info[m]["icon"]}
            for m in metricas
            if m in metrics
        ]
        html = render_to_string(
            "dashboard/partials/metrics_list.html",
            {"metrics_iter": metrics_iter, "metricas_selecionadas": metricas},
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
        inicio_str = request.GET.get("data_inicio")
        fim_str = request.GET.get("data_fim")
        inicio = datetime.fromisoformat(inicio_str) if inicio_str else None
        fim = datetime.fromisoformat(fim_str) if fim_str else None

        filters: dict[str, object] = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            value = request.GET.get(key)
            if value:
                filters[key] = value
        metricas_list = request.GET.getlist("metricas")
        if metricas_list:
            filters["metricas"] = metricas_list

        metrics = DashboardMetricsService.get_metrics(
            user,
            periodo=periodo,
            inicio=inicio,
            fim=fim,
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
                    f"{key}: total={data['total']} variação={data['crescimento']:.2f}%",
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
        writer.writerow(["Métrica", "Valor", "Variação (%)"])
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
        inicio = self.request.GET.get("data_inicio")
        fim = self.request.GET.get("data_fim")
        if inicio:
            config_data["filters"]["data_inicio"] = inicio
        if fim:
            config_data["filters"]["data_fim"] = fim
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            val = self.request.GET.get(key)
            if val:
                config_data["filters"][key] = val
        metricas_list = self.request.GET.getlist("metricas")
        if metricas_list:
            config_data["filters"]["metricas"] = metricas_list
        self.object = form.save(self.request.user, config_data)
        return redirect(self.get_success_url())


class DashboardConfigListView(LoginRequiredMixin, ListView):
    model = DashboardConfig
    template_name = "dashboard/config_list.html"

    def get_queryset(self):
        qs = DashboardConfig.objects.filter(user=self.request.user)
        public_qs = DashboardConfig.objects.filter(publico=True).exclude(user=self.request.user)
        if self.request.user.user_type == UserType.ROOT:
            qs = qs | public_qs
        else:
            qs = qs | public_qs.filter(user__organizacao=self.request.user.organizacao)
        return qs


class DashboardConfigApplyView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cfg = DashboardConfig.objects.filter(pk=pk).first()
        if not cfg:
            return HttpResponse(status=404)
        if cfg.user != request.user:
            if not cfg.publico:
                return HttpResponse(status=403)
            if (
                request.user.user_type != UserType.ROOT
                and cfg.user.organizacao_id != getattr(request.user, "organizacao_id", None)
            ):
                return HttpResponse(status=403)
        params = cfg.config.copy()
        filters = params.pop("filters", {})
        params.update(filters)
        url = reverse("dashboard:dashboard") + "?" + "&".join(
            f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in params.items()
        )
        return redirect(url)
