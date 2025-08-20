import csv
import io
import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import matplotlib.pyplot as plt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)
from openpyxl import Workbook

from accounts.models import UserType
from audit.services import hash_ip, log_audit
from core.permissions import (
    AdminRequiredMixin,
    ClienteRequiredMixin,
    GerenteRequiredMixin,
    SuperadminRequiredMixin,
)


from .forms import (
    DashboardConfigForm,
    DashboardCustomMetricForm,
    DashboardFilterForm,
    DashboardLayoutForm,
)

from agenda.models import Evento
from nucleos.models import Nucleo
from organizacoes.models import Organizacao


from .models import (
    Achievement,
    DashboardConfig,
    DashboardCustomMetric,
    DashboardFilter,
    DashboardLayout,
    UserAchievement,
)
from .services import (
    DashboardMetricsService,
    DashboardService,
    check_achievements,
    log_filter_action,
    log_layout_action,
)

User = get_user_model()

plt.switch_backend("Agg")

EXPORT_DIR = Path(settings.MEDIA_ROOT) / "dashboard_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

METRICAS_INFO = {
    "num_users": {"label": _("Usuários"), "icon": "fa-users"},
    "num_organizacoes": {"label": _("Organizações"), "icon": "fa-building"},
    "num_nucleos": {"label": _("Núcleos"), "icon": "fa-users-rectangle"},
    "num_empresas": {"label": _("Empresas"), "icon": "fa-city"},
    "num_eventos": {"label": _("Eventos"), "icon": "fa-calendar"},
    "num_posts_feed_total": {"label": _("Posts (Total)"), "icon": "fa-newspaper"},
    "num_posts_feed_recent": {"label": _("Posts (24h)"), "icon": "fa-clock"},
    "num_topicos": {"label": _("Tópicos"), "icon": "fa-comments"},
    "num_respostas": {"label": _("Respostas"), "icon": "fa-reply"},
    "num_mensagens_chat": {"label": _("Mensagens de chat"), "icon": "fa-comments"},
    "total_curtidas": {"label": _("Curtidas"), "icon": "fa-thumbs-up"},
    "total_compartilhamentos": {"label": _("Compartilhamentos"), "icon": "fa-share"},
    "tempo_medio_leitura": {
        "label": _("Tempo médio de leitura (s)"),
        "icon": "fa-book-open",
    },
    "inscricoes_confirmadas": {
        "label": _("Inscrições confirmadas"),
        "icon": "fa-user-check",
    },
    "lancamentos_pendentes": {
        "label": _("Lançamentos pendentes"),
        "icon": "fa-hourglass-half",
    },
    "posts_populares_24h": {"label": _("Posts populares 24h"), "icon": "fa-fire"},
    "tokens_gerados": {"label": _("Tokens gerados"), "icon": "fa-ticket"},
    "tokens_consumidos": {"label": _("Tokens consumidos"), "icon": "fa-ticket"},
}


class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """Base view para calcular métricas."""

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except PermissionError:
            messages.error(request, _("Acesso negado"))
            if request.headers.get("Hx-Request") == "true":
                html = render_to_string("dashboard/partials/messages.html", request=request)
                return HttpResponse(html, status=403)
            return HttpResponseForbidden(_("Acesso negado"))
        except ValueError as exc:
            messages.error(request, str(exc))
            if request.headers.get("Hx-Request") == "true":
                html = render_to_string("dashboard/partials/messages.html", request=request)
                return HttpResponse(html, status=400)
            return HttpResponseBadRequest(str(exc))

    def get_metrics(self):
        periodo = self.request.GET.get("periodo", "mensal")
        escopo = self.request.GET.get("escopo", "auto")

        inicio_str = self.request.GET.get("data_inicio")
        fim_str = self.request.GET.get("data_fim")
        try:
            inicio = datetime.fromisoformat(inicio_str) if inicio_str else None
        except ValueError:
            raise ValueError("data_inicio inválida")
        try:
            fim = datetime.fromisoformat(fim_str) if fim_str else None
        except ValueError:
            raise ValueError("data_fim inválida")

        filters: dict[str, object] = {}
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            value = self.request.GET.get(key)
            if value:
                filters[key] = value

        metricas_list = self.request.GET.getlist("metricas")
        if not metricas_list:
            metricas_list = [
                "num_users",
                "num_organizacoes",
                "num_nucleos",
                "num_empresas",
                "num_eventos",
                "inscricoes_confirmadas",
                "lancamentos_pendentes",
                "num_posts_feed_total",
            ]
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
        context["can_export"] = self.request.user.user_type in {
            UserType.ROOT,
            UserType.ADMIN,
            UserType.COORDENADOR,
        }
        metricas = self.filters.get("metricas") if hasattr(self, "filters") else None
        metricas = metricas or [
            "num_users",
            "inscricoes_confirmadas",
            "lancamentos_pendentes",
            "num_eventos",
            "num_posts_feed_total",
        ]
        context["metricas_selecionadas"] = metricas
        context["chart_data"] = [
            metrics[m]["total"] for m in metricas if m in metrics and isinstance(metrics[m]["total"], (int, float))
        ]
        context["metricas_disponiveis"] = [{"key": key, "label": data["label"]} for key, data in METRICAS_INFO.items()]
        context["metricas_iter"] = [
            {"key": m, "data": metrics[m], "label": METRICAS_INFO[m]["label"], "icon": METRICAS_INFO[m]["icon"]}
            for m in metricas
            if m in metrics
        ]
        obtidas = UserAchievement.objects.filter(user=self.request.user).count()
        context["has_pending_achievements"] = Achievement.objects.count() > obtidas
        user = self.request.user
        if user.user_type in {UserType.ROOT, UserType.ADMIN}:
            orgs = Organizacao.objects.all()
            nucleos = Nucleo.objects.all()
            eventos = Evento.objects.all()
        else:
            org_id = getattr(user.organizacao, "pk", None)
            orgs = Organizacao.objects.filter(pk=org_id) if org_id else Organizacao.objects.none()
            nucleos = Nucleo.objects.filter(
                participacoes__user=user,
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            ).distinct()
            eventos = Evento.objects.filter(
                Q(coordenador=user)
                | Q(
                    nucleo__participacoes__user=user,
                    nucleo__participacoes__status="ativo",
                    nucleo__participacoes__status_suspensao=False,
                )
            ).distinct()
        context["organizacoes_permitidas"] = orgs
        context["nucleos_permitidos"] = nucleos
        context["eventos_permitidos"] = eventos
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
        metricas = request.GET.getlist("metricas") or list(METRICAS_INFO.keys())
        metrics = DashboardMetricsService.get_metrics(request.user, metricas=metricas)
        metricas_iter = [
            {
                "key": m,
                "data": metrics[m],
                "label": METRICAS_INFO[m]["label"],
                "icon": METRICAS_INFO[m]["icon"],
            }
            for m in metricas
            if m in metrics
        ]
        html = render_to_string(
            "dashboard/partials/metrics_list.html",
            {"metricas_iter": metricas_iter, "metricas_selecionadas": metricas},
            request=request,
        )
        return HttpResponse(html)
    except PermissionError:
        messages.error(request, _("Acesso negado"))
        html = render_to_string("dashboard/partials/messages.html", request=request)
        return HttpResponse(html, status=403)
    except ValueError as exc:
        messages.error(request, str(exc))
        html = render_to_string("dashboard/partials/messages.html", request=request)
        return HttpResponse(html, status=400)
    except Exception:  # pragma: no cover - logado
        messages.error(request, _("Erro ao carregar métricas."))
        html = render_to_string("dashboard/partials/messages.html", request=request)
        return HttpResponse(html, status=500)


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

        def _response_with_message(msg: str, status: int) -> HttpResponse:
            messages.error(request, msg)
            if request.headers.get("Hx-Request") == "true":
                html = render_to_string(
                    "dashboard/partials/messages.html", request=request
                )
                return HttpResponse(html, status=status)
            return HttpResponse(msg, status=status)

        if user.user_type not in {UserType.ROOT, UserType.ADMIN, UserType.COORDENADOR}:
            return _response_with_message(_("Acesso negado"), 403)

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

        try:
            metrics = DashboardMetricsService.get_metrics(
                user,
                periodo=periodo,
                inicio=inicio,
                fim=fim,
                escopo=escopo,
                **filters,
            )
        except PermissionError:
            return _response_with_message(_("Acesso negado"), 403)
        except ValueError as exc:
            return _response_with_message(str(exc), 400)

        if formato == "pdf":
            try:
                from weasyprint import HTML
            except Exception:
                return _response_with_message(_("PDF indisponível"), 500)
            html = render_to_string("dashboard/export_pdf.html", {"metrics": metrics})
            pdf_bytes = HTML(string=html).write_pdf()
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            filename = datetime.now().strftime("metrics_%Y%m%d_%H%M%S.pdf")
            resp["Content-Disposition"] = f"attachment; filename={filename}"
            log_audit(
                user=request.user,
                action="EXPORT_PDF",
                object_type="DashboardMetrics",
                object_id="",
                ip_hash=hash_ip(request.META.get("REMOTE_ADDR", "")),
                status="SUCCESS",
                metadata={"formato": formato, **filters},
            )
            return resp

        if formato == "xlsx":
            wb = Workbook()
            ws = wb.active
            ws.title = "Métricas"
            ws.append(["Métrica", "Valor", "Variação (%)"])
            for key, data in metrics.items():
                ws.append([key, data["total"], data["crescimento"]])
            output = io.BytesIO()
            wb.save(output)
            resp = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            filename = datetime.now().strftime("metrics_%Y%m%d_%H%M%S.xlsx")
            resp["Content-Disposition"] = f"attachment; filename={filename}"
            log_audit(
                user=request.user,
                action="EXPORT_XLSX",
                object_type="DashboardMetrics",
                object_id="",
                ip_hash=hash_ip(request.META.get("REMOTE_ADDR", "")),
                status="SUCCESS",
                metadata={"formato": formato, **filters},
            )
            return resp

        if formato == "png":
            keys = list(metrics.keys())
            values = [data["total"] for data in metrics.values()]
            fig, ax = plt.subplots()
            ax.bar(keys, values)
            ax.set_ylabel("Valor")
            ax.set_title("Métricas")
            filename = datetime.now().strftime("metrics_%Y%m%d_%H%M%S.png")
            filepath = EXPORT_DIR / filename
            fig.savefig(filepath)
            plt.close(fig)
            log_audit(
                user=request.user,
                action="EXPORT_PNG",
                object_type="DashboardMetrics",
                object_id="",
                ip_hash=hash_ip(request.META.get("REMOTE_ADDR", "")),
                status="SUCCESS",
                metadata={"formato": formato, **filters},
            )
            return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

        # default csv
        resp = HttpResponse(content_type="text/csv")
        filename = datetime.now().strftime("metrics_%Y%m%d_%H%M%S.csv")
        resp["Content-Disposition"] = f"attachment; filename={filename}"
        writer = csv.writer(resp)
        writer.writerow(["Métrica", "Valor", "Variação (%)"])
        for key, data in metrics.items():
            writer.writerow([key, data["total"], data["crescimento"]])
        log_audit(
            user=request.user,
            action="EXPORT_CSV",
            object_type="DashboardMetrics",
            object_id="",
            ip_hash=hash_ip(request.META.get("REMOTE_ADDR", "")),
            status="SUCCESS",
            metadata={"formato": formato, **filters},
        )
        return resp


class DashboardExportedImageView(LoginRequiredMixin, View):
    """Serve imagens de exportações já geradas."""

    def get(self, request, filename: str):
        if request.user.user_type not in {UserType.ROOT, UserType.ADMIN, UserType.COORDENADOR}:
            return HttpResponse(status=403)
        path = EXPORT_DIR / filename
        if not path.exists():
            return HttpResponse(status=404)
        return FileResponse(open(path, "rb"), content_type="image/png")


class AchievementListView(LoginRequiredMixin, ListView):
    model = Achievement
    template_name = "dashboard/achievement_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_achievements = set(
            UserAchievement.objects.filter(user=self.request.user).values_list("achievement_id", flat=True)
        )
        ctx["user_achievements"] = user_achievements
        return ctx


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
        check_achievements(self.request.user)
        action = "SHARE_DASHBOARD" if self.object.publico else "CREATE_CONFIG"
        log_audit(
            user=self.request.user,
            action=action,
            object_type="DashboardConfig",
            object_id=str(self.object.pk),
            ip_hash=hash_ip(self.request.META.get("REMOTE_ADDR", "")),
            status="SUCCESS",
            metadata=config_data,
        )
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
            if request.user.user_type != UserType.ROOT and cfg.user.organizacao_id != getattr(
                request.user, "organizacao_id", None
            ):
                return HttpResponse(status=403)
        params = cfg.config.copy()
        filters = params.pop("filters", {})
        params.update(filters)
        url = (
            reverse("dashboard:dashboard")
            + "?"
            + "&".join(f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in params.items())
        )
        log_audit(
            user=request.user,
            action="APPLY_CONFIG",
            object_type="DashboardConfig",
            object_id=str(cfg.pk),
            ip_hash=hash_ip(request.META.get("REMOTE_ADDR", "")),
            status="SUCCESS",
            metadata=params,
        )
        return redirect(url)


class DashboardConfigUpdateView(LoginRequiredMixin, UpdateView):
    model = DashboardConfig
    form_class = DashboardConfigForm
    template_name = "dashboard/config_form.html"

    def get_success_url(self):
        return reverse("dashboard:configs")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user != request.user and request.user.user_type not in {
            UserType.ROOT,
            UserType.ADMIN,
        }:
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

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
        self.object = form.save(form.instance.user, config_data)
        log_audit(
            user=self.request.user,
            action="UPDATE_CONFIG",
            object_type="DashboardConfig",
            object_id=str(self.object.pk),
            ip_hash=hash_ip(self.request.META.get("REMOTE_ADDR", "")),
            status="SUCCESS",
            metadata=config_data,
        )
        return redirect(self.get_success_url())


class DashboardConfigDeleteView(LoginRequiredMixin, DeleteView):
    model = DashboardConfig
    template_name = "dashboard/config_confirm_delete.html"

    def get_success_url(self):
        return reverse("dashboard:configs")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user != request.user and request.user.user_type not in {
            UserType.ROOT,
            UserType.ADMIN,
        }:
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        pk = str(obj.pk)
        response = super().delete(request, *args, **kwargs)
        log_audit(
            user=request.user,
            action="DELETE_CONFIG",
            object_type="DashboardConfig",
            object_id=pk,
            ip_hash=hash_ip(request.META.get("REMOTE_ADDR", "")),
            status="SUCCESS",
            metadata={},
        )
        return response


class DashboardFilterCreateView(LoginRequiredMixin, CreateView):
    form_class = DashboardFilterForm
    template_name = "dashboard/filter_form.html"

    def get_success_url(self):
        return reverse("dashboard:filters")

    def form_valid(self, form):
        filtros_data = {}
        for key, value in self.request.GET.lists():
            if key == "metricas":
                filtros_data[key] = value
            else:
                filtros_data[key] = value[0]
        self.object = form.save(self.request.user, filtros_data)
        check_achievements(self.request.user)
        log_filter_action(
            user=self.request.user,
            action="CREATE_FILTER",
            filtro=self.object,
            ip_address=self.request.META.get("REMOTE_ADDR", ""),
            metadata=filtros_data,
        )
        return redirect(self.get_success_url())


class DashboardFilterListView(LoginRequiredMixin, ListView):
    model = DashboardFilter
    template_name = "dashboard/filter_list.html"

    def get_queryset(self):
        qs = DashboardFilter.objects.filter(user=self.request.user)
        public_qs = DashboardFilter.objects.filter(publico=True).exclude(user=self.request.user)
        if self.request.user.user_type == UserType.ROOT:
            qs = qs | public_qs
        else:
            qs = qs | public_qs.filter(user__organizacao=self.request.user.organizacao)
        return qs


class DashboardFilterApplyView(LoginRequiredMixin, View):
    def get(self, request, pk):
        filtro = DashboardFilter.objects.filter(pk=pk).first()
        if not filtro:
            return HttpResponse(status=404)
        if filtro.user != request.user:
            if not filtro.publico:
                return HttpResponse(status=403)
            if request.user.user_type != UserType.ROOT and filtro.user.organizacao_id != getattr(
                request.user, "organizacao_id", None
            ):
                return HttpResponse(status=403)
        url = reverse("dashboard:dashboard") + "?" + urlencode(filtro.filtros, doseq=True)
        log_filter_action(
            user=request.user,
            action="APPLY_FILTER",
            filtro=filtro,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            metadata={"filtros": filtro.filtros},
        )
        return redirect(url)


class DashboardFilterUpdateView(LoginRequiredMixin, UpdateView):
    model = DashboardFilter
    form_class = DashboardFilterForm
    template_name = "dashboard/filter_form.html"

    def get_success_url(self):
        return reverse("dashboard:filters")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user != request.user and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        filtros_data = {}
        for key, value in self.request.GET.lists():
            if key == "metricas":
                filtros_data[key] = value
            else:
                filtros_data[key] = value[0]
        self.object = form.save(self.request.user, filtros_data)
        log_filter_action(
            user=self.request.user,
            action="UPDATE_FILTER",
            filtro=self.object,
            ip_address=self.request.META.get("REMOTE_ADDR", ""),
            metadata=filtros_data,
        )
        return redirect(self.get_success_url())


class DashboardFilterDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        filtro = DashboardFilter.objects.filter(pk=pk).first()
        if not filtro:
            return HttpResponse(status=404)
        if filtro.user != request.user and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            return HttpResponse(status=403)
        filtro.delete()
        log_filter_action(
            user=request.user,
            action="DELETE_FILTER",
            filtro=filtro,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            metadata={"filtros": filtro.filtros},
        )
        return redirect("dashboard:filters")


class DashboardLayoutListView(LoginRequiredMixin, ListView):
    model = DashboardLayout
    template_name = "dashboard/layout_list.html"

    def get_queryset(self):
        if self.request.user.user_type in {UserType.ROOT, UserType.ADMIN}:
            return DashboardLayout.objects.all()
        return DashboardLayout.objects.filter(Q(user=self.request.user) | Q(publico=True))


class DashboardLayoutCreateView(LoginRequiredMixin, CreateView):
    model = DashboardLayout
    form_class = DashboardLayoutForm
    template_name = "dashboard/layout_form.html"
    success_url = "/dashboard/layouts/"

    def form_valid(self, form):
        layout_data = self.request.POST.get("layout_json", "{}")
        self.object = form.save(self.request.user, layout_data)
        log_layout_action(
            user=self.request.user,
            action="CREATE_LAYOUT",
            layout=self.object,
            ip_address=self.request.META.get("REMOTE_ADDR", ""),
        )
        return redirect(self.get_success_url())


class DashboardLayoutUpdateView(LoginRequiredMixin, UpdateView):
    model = DashboardLayout
    form_class = DashboardLayoutForm
    template_name = "dashboard/layout_form.html"
    success_url = "/dashboard/layouts/"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user != request.user and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            return HttpResponse(status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        layout = self.object
        context["layout_save_url"] = reverse("dashboard:layout-save", args=[layout.pk])
        layout_data = layout.layout_json
        if isinstance(layout_data, str):
            try:
                metricas = json.loads(layout_data)
            except Exception:
                metricas = []
        else:
            metricas = layout_data or []
        if not metricas:
            metricas = list(METRICAS_INFO.keys())
        metrics = DashboardMetricsService.get_metrics(self.request.user, metricas=metricas)
        context["metricas_iter"] = [
            {
                "key": m,
                "data": metrics[m],
                "label": METRICAS_INFO[m]["label"],
                "icon": METRICAS_INFO[m]["icon"],
            }
            for m in metricas
            if m in metrics
        ]
        context["metricas_selecionadas"] = metricas
        return context

    def form_valid(self, form):
        layout_data = self.request.POST.get("layout_json")
        if not layout_data:
            layout_data = self.get_object().layout_json
        self.object = form.save(self.request.user, layout_data)
        log_layout_action(
            user=self.request.user,
            action="UPDATE_LAYOUT",
            layout=self.object,
            ip_address=self.request.META.get("REMOTE_ADDR", ""),
        )
        return redirect(self.get_success_url())


class DashboardLayoutDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        layout = DashboardLayout.objects.filter(pk=pk).first()
        if not layout:
            return HttpResponse(status=404)
        if layout.user != request.user and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            return HttpResponse(status=403)
        layout.delete()
        log_layout_action(
            user=request.user,
            action="DELETE_LAYOUT",
            layout=layout,
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )
        return redirect("/dashboard/layouts/")


class DashboardLayoutSaveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        layout = DashboardLayout.objects.filter(pk=pk).first()
        if not layout:
            return HttpResponse(status=404)
        if layout.user != request.user and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
            return HttpResponse(status=403)
        layout_json = request.POST.get("layout_json")
        if layout_json:
            layout.layout_json = layout_json
            layout.save(update_fields=["layout_json", "updated_at"])
            log_layout_action(
                user=request.user,
                action="SAVE_LAYOUT",
                layout=layout,
                ip_address=request.META.get("REMOTE_ADDR", ""),
            )
        return HttpResponse(status=204)


class DashboardCustomMetricListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = DashboardCustomMetric
    template_name = "dashboard/custom_metric_list.html"


class DashboardCustomMetricCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = DashboardCustomMetric
    form_class = DashboardCustomMetricForm
    template_name = "dashboard/custom_metric_form.html"

    def get_success_url(self):
        return reverse("dashboard:custom-metrics")


class DashboardCustomMetricUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = DashboardCustomMetric
    form_class = DashboardCustomMetricForm
    template_name = "dashboard/custom_metric_form.html"

    def get_success_url(self):
        return reverse("dashboard:custom-metrics")


class DashboardCustomMetricDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = DashboardCustomMetric
    template_name = "dashboard/custom_metric_confirm_delete.html"

    def get_success_url(self):
        return reverse("dashboard:custom-metrics")
