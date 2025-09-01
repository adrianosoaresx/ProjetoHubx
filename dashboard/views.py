import io
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from django.utils import timezone
from django.utils.dateparse import parse_datetime

import matplotlib.pyplot as plt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
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

from accounts.models import UserType
from agenda.models import Evento
from audit.services import hash_ip, log_audit
from tokens.utils import get_client_ip
from core.permissions import (
    AdminRequiredMixin,
    ClienteRequiredMixin,
    GerenteRequiredMixin,
    SuperadminRequiredMixin,
)
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .forms import (
    DashboardConfigForm,
    DashboardCustomMetricForm,
    DashboardFilterForm,
    DashboardLayoutForm,
)
from .models import (
    DashboardConfig,
    DashboardCustomMetric,
    DashboardFilter,
    DashboardLayout,
)
from .services import (
    DashboardMetricsService,
    DashboardService,
    log_filter_action,
    log_layout_action,
)
from .constants import METRICAS_INFO

User = get_user_model()

logger = logging.getLogger(__name__)

plt.switch_backend("Agg")

EXPORT_DIR = Path(settings.MEDIA_ROOT) / "dashboard_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)



class DashboardBaseView(LoginRequiredMixin, TemplateView):
    """Base view para calcular métricas."""

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except PermissionError:
            messages.error(request, _("Acesso negado"))
            if request.headers.get("Hx-Request") == "true":
                html = render_to_string(
                    "dashboard/partials/filters_form.html",
                    self.get_filters_context(),
                    request=request,
                )
                return HttpResponse(html, status=403)
            return HttpResponseForbidden(_("Acesso negado"))
        except ValueError as exc:
            messages.error(request, str(exc))
            if request.headers.get("Hx-Request") == "true":
                html = render_to_string(
                    "dashboard/partials/filters_form.html",
                    self.get_filters_context(),
                    request=request,
                )
                return HttpResponse(html, status=400)
            return HttpResponseBadRequest(str(exc))

    def get_metrics(self):
        periodo = self.request.GET.get("periodo", "mensal")
        escopo = self.request.GET.get("escopo", "auto")

        inicio_str = self.request.GET.get("data_inicio")
        fim_str = self.request.GET.get("data_fim")
        inicio = parse_datetime(inicio_str) if inicio_str else None
        if inicio_str and inicio is None:
            raise ValueError("data_inicio inválida")
        if inicio and timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio)
        fim = parse_datetime(fim_str) if fim_str else None
        if fim_str and fim is None:
            raise ValueError("data_fim inválida")
        if fim and timezone.is_naive(fim):
            fim = timezone.make_aware(fim)
        if inicio and fim and inicio > fim:
            raise ValueError("data_inicio deve ser menor ou igual a data_fim")

        user = self.request.user
        filters: dict[str, object] = {}
        org_id = self.request.GET.get("organizacao_id")
        nucleo_id = self.request.GET.get("nucleo_id")
        evento_id = self.request.GET.get("evento_id")

        if user.user_type in {UserType.ROOT, UserType.ADMIN}:
            if org_id:
                filters["organizacao_id"] = org_id
            if nucleo_id:
                filters["nucleo_id"] = nucleo_id
            if evento_id:
                filters["evento_id"] = evento_id
        else:
            user_org_id = getattr(user, "organizacao_id", None)
            if org_id and str(user_org_id) != org_id:
                raise PermissionError("Organização não permitida")
            if user_org_id:
                filters["organizacao_id"] = str(user_org_id)

            if nucleo_id:
                allowed_nucleos = {
                    str(pk)
                    for pk in user.nucleos.values_list("id", flat=True)
                }
                if nucleo_id not in allowed_nucleos:
                    raise PermissionError("Núcleo não permitido")
                filters["nucleo_id"] = nucleo_id

            if evento_id:
                allowed_eventos = {
                    str(pk)
                    for pk in Evento.objects.filter(
                        Q(coordenador=user)
                        | Q(
                            nucleo__participacoes__user=user,
                            nucleo__participacoes__status="ativo",
                            nucleo__participacoes__status_suspensao=False,
                        )
                    ).values_list("id", flat=True)
                }
                if evento_id not in allowed_eventos:
                    raise PermissionError("Evento não permitido")
                filters["evento_id"] = evento_id

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
        else:
            valid_metricas = set(METRICAS_INFO.keys()) | set(
                DashboardCustomMetric.objects.values_list("code", flat=True)
            )
            invalid = [m for m in metricas_list if m not in valid_metricas]
            if invalid:
                if len(invalid) == 1:
                    raise ValueError(f"Métrica inválida: {invalid[0]}")
                raise ValueError(f"Métricas inválidas: {', '.join(invalid)}")
        filters["metricas"] = metricas_list

        self.periodo = periodo
        self.escopo = escopo
        self.filters = {**filters, "data_inicio": inicio_str, "data_fim": fim_str}

        metrics, metricas_info = DashboardMetricsService.get_metrics(
            self.request.user,
            periodo=periodo,
            inicio=inicio,
            fim=fim,
            escopo=escopo,
            **filters,
        )
        self.metricas_info = metricas_info
        return metrics, metricas_info

    def get_filters_context(self):
        request = self.request
        periodo = request.GET.get("periodo", "mensal")
        escopo = request.GET.get("escopo", "auto")
        filtros = {
            "organizacao_id": request.GET.get("organizacao_id"),
            "nucleo_id": request.GET.get("nucleo_id"),
            "evento_id": request.GET.get("evento_id"),
            "data_inicio": request.GET.get("data_inicio"),
            "data_fim": request.GET.get("data_fim"),
        }
        can_export = request.user.user_type in {
            UserType.ROOT,
            UserType.ADMIN,
            UserType.COORDENADOR,
        }
        metricas = request.GET.getlist("metricas") or [
            "num_users",
            "inscricoes_confirmadas",
            "lancamentos_pendentes",
            "num_eventos",
            "num_posts_feed_total",
        ]
        metricas_info = getattr(self, "metricas_info", METRICAS_INFO)
        metricas_disponiveis = [
            {"key": key, "label": data["label"]} for key, data in metricas_info.items()
        ]
        user = request.user
        def limit_with_selected(qs, selected_id, limit=50):
            if selected_id:
                return qs.filter(pk=selected_id) | qs.exclude(pk=selected_id)[: limit - 1]
            return qs[:limit]

        if user.user_type in {UserType.ROOT, UserType.ADMIN}:
            orgs_qs = Organizacao.objects.only("id", "nome")
            nucleos_qs = (
                Nucleo.objects.only("id", "nome", "organizacao")
                .select_related("organizacao")
            )
            eventos_qs = (
                Evento.objects.only("id", "titulo", "nucleo", "organizacao")
                .select_related("nucleo", "organizacao")
            )
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

            orgs_qs = (
                Organizacao.objects.filter(pk=org_id).only("id", "nome")
                if org_id
                else Organizacao.objects.none()
            )
            nucleos_qs = (
                Nucleo.objects.filter(
                    participacoes__user=user,
                    participacoes__status="ativo",
                    participacoes__status_suspensao=False,
                )
                .distinct()
                .only("id", "nome", "organizacao")
                .select_related("organizacao")
            )
            eventos_qs = (
                Evento.objects.filter(
                    Q(coordenador=user)
                    | Q(
                        nucleo__participacoes__user=user,
                        nucleo__participacoes__status="ativo",
                        nucleo__participacoes__status_suspensao=False,
                    )
                )
                .distinct()
                .only("id", "titulo", "nucleo", "organizacao")
                .select_related("nucleo", "organizacao")
            )

        orgs = limit_with_selected(orgs_qs, filtros["organizacao_id"])
        nucleos = limit_with_selected(nucleos_qs, filtros["nucleo_id"])
        eventos = limit_with_selected(eventos_qs, filtros["evento_id"])

        return {
            "periodo": periodo,
            "escopo": escopo,
            "filtros": filtros,
            "can_export": can_export,
            "metricas_selecionadas": metricas,
            "metricas_disponiveis": metricas_disponiveis,
            "organizacoes_permitidas": orgs,
            "nucleos_permitidos": nucleos,
            "eventos_permitidos": eventos,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metrics, metricas_info = self.get_metrics()
        context.update(metrics)
        context["metrics_data"] = metrics
        context.update(self.get_filters_context())
        metricas = context["metricas_selecionadas"]
        context["chart_data"] = [
            metrics[m]["total"]
            for m in metricas
            if m in metrics and isinstance(metrics[m]["total"], (int, float))
        ]
        context["metricas_iter"] = [
            {
                "key": m,
                "data": metrics[m],
                "label": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("label"),
                "icon": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("icon"),
            }
            for m in metricas
            if m in metrics
        ]
        context["metricas_info"] = metricas_info
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
        context["organizacoes"] = (
            Organizacao.objects.annotate(
                num_users=Count("users", distinct=True),
                num_nucleos=Count("nucleos", distinct=True),
                num_eventos=Count("evento", distinct=True),
            )
            .all()
        )
        return context


class AdminDashboardView(AdminRequiredMixin, DashboardBaseView):
    template_name = "dashboard/admin.html"


class CoordenadorDashboardView(GerenteRequiredMixin, DashboardBaseView):
    template_name = "dashboard/coordenador.html"


class ClienteDashboardView(ClienteRequiredMixin, DashboardBaseView):
    template_name = "dashboard/cliente.html"


def dashboard_redirect(request):
    """Redireciona usuário para o dashboard apropriado."""
    user = request.user
    if not user.is_authenticated:
        return redirect("accounts:login")

    user_type = getattr(user, "user_type", None) or getattr(user, "get_tipo_usuario", None)

    if user.is_superuser or user_type in {UserType.ROOT, UserType.ROOT.value}:
        return redirect("dashboard:root")
    if user_type in {UserType.ADMIN, UserType.ADMIN.value}:
        return redirect("dashboard:admin")
    if user_type in {UserType.COORDENADOR, UserType.COORDENADOR.value}:
        return redirect("dashboard:coordenador")
    if user_type in {
        UserType.ASSOCIADO,
        UserType.ASSOCIADO.value,
        UserType.NUCLEADO,
        UserType.NUCLEADO.value,
    }:
        return redirect("dashboard:cliente")
    return redirect("accounts:perfil")


def metrics_partial(request):
    """Retorna HTML com métricas para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.has_perm("dashboard.view_metrics"):
        return HttpResponse(status=403)
    try:
        metricas = request.GET.getlist("metricas") or list(METRICAS_INFO.keys())
        metrics, metricas_info = DashboardMetricsService.get_metrics(
            request.user, metricas=metricas
        )
        metricas_iter = [
            {
                "key": m,
                "data": metrics[m],
                "label": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("label"),
                "icon": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("icon"),
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
        logger.exception("Acesso negado ao carregar métricas")
        messages.error(request, _("Acesso negado"))
        html = render_to_string("dashboard/partials/messages.html", request=request)
        return HttpResponse(html, status=403)
    except ValueError as exc:
        logger.exception("Erro de valor ao carregar métricas")
        messages.error(request, str(exc))
        html = render_to_string("dashboard/partials/messages.html", request=request)
        return HttpResponse(html, status=400)
    except Exception:  # pragma: no cover - logado
        logger.exception("Erro inesperado ao carregar métricas")
        messages.error(request, _("Erro ao carregar métricas."))
        html = render_to_string("dashboard/partials/messages.html", request=request)
        return HttpResponse(html, status=500)


def lancamentos_partial(request):
    """Últimos lançamentos financeiros."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.has_perm("dashboard.view_metrics"):
        return HttpResponse(status=403)
    try:
        lancamentos = DashboardService.ultimos_lancamentos(request.user)
        html = render_to_string(
            "dashboard/partials/latest_transactions.html",
            {"lancamentos": lancamentos},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover - logado
        logger.exception("Erro ao carregar lançamentos")
        messages.error(request, _("Erro ao carregar lançamentos."))
        return HttpResponse(status=500)


def notificacoes_partial(request):
    """Notificações recentes para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.has_perm("dashboard.view_metrics"):
        return HttpResponse(status=403)
    try:
        notificacoes = DashboardService.ultimas_notificacoes(request.user)
        html = render_to_string(
            "dashboard/partials/notifications_list.html",
            {"notificacoes": notificacoes},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover
        logger.exception("Erro ao carregar notificações")
        messages.error(request, _("Erro ao carregar notificações."))
        return HttpResponse(status=500)


def tarefas_partial(request):
    """Tarefas pendentes para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.has_perm("dashboard.view_metrics"):
        return HttpResponse(status=403)
    try:
        tarefas = DashboardService.tarefas_pendentes(request.user)
        html = render_to_string(
            "dashboard/partials/pending_tasks.html",
            {"tarefas": tarefas},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover
        logger.exception("Erro ao carregar tarefas")
        messages.error(request, _("Erro ao carregar tarefas."))
        return HttpResponse(status=500)


def organizacoes_search(request):
    """Busca assíncrona de organizações para Select2."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    term = request.GET.get("q", "")
    user = request.user

    if user.user_type in {UserType.ROOT, UserType.ADMIN}:
        qs = (
            Organizacao.objects.only("id", "nome")
            .filter(nome__icontains=term)[:50]
        )
    else:
        org_id = getattr(user, "organizacao_id", None)
        if not org_id:
            return HttpResponse(status=403)
        qs = (
            Organizacao.objects.only("id", "nome")
            .filter(id=org_id, nome__icontains=term)[:50]
        )

    data = {"results": [{"id": o.id, "text": o.nome} for o in qs]}
    return JsonResponse(data)


def nucleos_search(request):
    """Busca assíncrona de núcleos para Select2."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    term = request.GET.get("q", "")
    user = request.user
    qs = Nucleo.objects.only("id", "nome", "organizacao").select_related("organizacao")

    if user.user_type in {UserType.ROOT, UserType.ADMIN}:
        qs = qs.filter(nome__icontains=term)[:50]
    else:
        allowed_ids = list(user.nucleos.values_list("id", flat=True))
        if not allowed_ids:
            return HttpResponse(status=403)
        qs = qs.filter(id__in=allowed_ids, nome__icontains=term)[:50]

    data = {"results": [{"id": n.id, "text": n.nome} for n in qs]}
    return JsonResponse(data)


def eventos_search(request):
    """Busca assíncrona de eventos para Select2."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    term = request.GET.get("q", "")
    user = request.user
    qs = Evento.objects.only("id", "titulo", "nucleo", "organizacao").select_related(
        "nucleo", "organizacao"
    )

    if user.user_type in {UserType.ROOT, UserType.ADMIN}:
        qs = qs.filter(titulo__icontains=term)[:50]
    else:
        allowed_ids = list(
            Evento.objects.filter(
                Q(coordenador=user)
                | Q(
                    nucleo__participacoes__user=user,
                    nucleo__participacoes__status="ativo",
                    nucleo__participacoes__status_suspensao=False,
                )
            ).values_list("id", flat=True)
        )
        if not allowed_ids:
            return HttpResponse(status=403)
        qs = qs.filter(id__in=allowed_ids, titulo__icontains=term)[:50]

    data = {"results": [{"id": e.id, "text": e.titulo} for e in qs]}
    return JsonResponse(data)


def eventos_partial(request):
    """Próximos eventos para HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if not request.user.has_perm("dashboard.view_metrics"):
        return HttpResponse(status=403)
    try:
        eventos = DashboardService.proximos_eventos(request.user)
        html = render_to_string(
            "dashboard/partials/upcoming_events.html",
            {"eventos": eventos},
            request=request,
        )
        return HttpResponse(html)
    except Exception:  # pragma: no cover
        logger.exception("Erro ao carregar eventos")
        messages.error(request, _("Erro ao carregar eventos."))
        return HttpResponse(status=500)


class DashboardExportView(LoginRequiredMixin, View):
    """Exporta métricas em PDF ou PNG."""

    def get(self, request):
        user = request.user

        def _response_with_message(msg: str, status: int) -> HttpResponse:
            messages.error(request, msg)
            if request.headers.get("Hx-Request") == "true":
                html = render_to_string("dashboard/partials/messages.html", request=request)
                return HttpResponse(html, status=status)
            return HttpResponse(msg, status=status)

        if user.user_type not in {UserType.ROOT, UserType.ADMIN, UserType.COORDENADOR}:
            return _response_with_message(_("Acesso negado"), 403)

        periodo = request.GET.get("periodo", "mensal")
        escopo = request.GET.get("escopo", "auto")
        formato = request.GET.get("formato", "pdf")
        audit_action = f"EXPORT_{formato.upper()}"
        inicio_str = request.GET.get("data_inicio")
        fim_str = request.GET.get("data_fim")
        inicio = parse_datetime(inicio_str) if inicio_str else None
        if inicio_str and inicio is None:
            return _response_with_message(_("data_inicio inválida"), 400)
        if inicio and timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio)
        fim = parse_datetime(fim_str) if fim_str else None
        if fim_str and fim is None:
            return _response_with_message(_("data_fim inválida"), 400)
        if fim and timezone.is_naive(fim):
            fim = timezone.make_aware(fim)

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
            log_audit(
                user=request.user,
                action=audit_action,
                object_type="DashboardMetrics",
                object_id="",
                ip_hash=hash_ip(get_client_ip(request)),
                status="ERROR",
                metadata={"formato": formato, **filters},
            )
            return _response_with_message(_("Acesso negado"), 403)
        except ValueError as exc:
            log_audit(
                user=request.user,
                action=audit_action,
                object_type="DashboardMetrics",
                object_id="",
                ip_hash=hash_ip(get_client_ip(request)),
                status="ERROR",
                metadata={"formato": formato, **filters},
            )
            return _response_with_message(str(exc), 400)

        if formato == "pdf":
            try:
                from weasyprint import HTML
            except Exception:
                log_audit(
                    user=request.user,
                    action="EXPORT_PDF",
                    object_type="DashboardMetrics",
                    object_id="",
                    ip_hash=hash_ip(get_client_ip(request)),
                    status="ERROR",
                    metadata={"formato": formato, **filters},
                )
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
                ip_hash=hash_ip(get_client_ip(request)),
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
                ip_hash=hash_ip(get_client_ip(request)),
                status="SUCCESS",
                metadata={"formato": formato, **filters},
            )
            return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

        return _response_with_message(_("Formato inválido"), 400)


class DashboardExportedImageView(LoginRequiredMixin, View):
    """Serve imagens de exportações já geradas."""

    def get(self, request, filename: str):
        if request.user.user_type not in {UserType.ROOT, UserType.ADMIN, UserType.COORDENADOR}:
            return HttpResponse(status=403)
        try:
            path = (EXPORT_DIR / filename).resolve(strict=True)
            path.relative_to(EXPORT_DIR.resolve())
        except (FileNotFoundError, ValueError):
            return HttpResponse(status=404)
        if not path.is_file():
            return HttpResponse(status=404)
        return FileResponse(open(path, "rb"), content_type="image/png")


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
        inicio_str = self.request.GET.get("data_inicio")
        fim_str = self.request.GET.get("data_fim")
        inicio_dt = parse_datetime(inicio_str) if inicio_str else None
        if inicio_dt:
            if timezone.is_naive(inicio_dt):
                inicio_dt = timezone.make_aware(inicio_dt)
            config_data["filters"]["data_inicio"] = inicio_dt.isoformat()
        fim_dt = parse_datetime(fim_str) if fim_str else None
        if fim_dt:
            if timezone.is_naive(fim_dt):
                fim_dt = timezone.make_aware(fim_dt)
            config_data["filters"]["data_fim"] = fim_dt.isoformat()
        for key in ["organizacao_id", "nucleo_id", "evento_id"]:
            val = self.request.GET.get(key)
            if val:
                config_data["filters"][key] = val
        metricas_list = self.request.GET.getlist("metricas")
        if metricas_list:
            config_data["filters"]["metricas"] = metricas_list
        self.object = form.save(self.request.user, config_data)
        action = "SHARE_DASHBOARD" if self.object.publico else "CREATE_CONFIG"
        log_audit(
            user=self.request.user,
            action=action,
            object_type="DashboardConfig",
            object_id=str(self.object.pk),
            ip_hash=hash_ip(get_client_ip(self.request)),
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
            ip_hash=hash_ip(get_client_ip(request)),
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
        inicio_str = self.request.GET.get("data_inicio")
        fim_str = self.request.GET.get("data_fim")
        inicio_dt = parse_datetime(inicio_str) if inicio_str else None
        if inicio_dt:
            if timezone.is_naive(inicio_dt):
                inicio_dt = timezone.make_aware(inicio_dt)
            config_data["filters"]["data_inicio"] = inicio_dt.isoformat()
        fim_dt = parse_datetime(fim_str) if fim_str else None
        if fim_dt:
            if timezone.is_naive(fim_dt):
                fim_dt = timezone.make_aware(fim_dt)
            config_data["filters"]["data_fim"] = fim_dt.isoformat()
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
            ip_hash=hash_ip(get_client_ip(self.request)),
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
            ip_hash=hash_ip(get_client_ip(request)),
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
        log_filter_action(
            user=self.request.user,
            action="CREATE_FILTER",
            filtro=self.object,
            ip_address=get_client_ip(self.request),
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
            ip_address=get_client_ip(request),
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
            ip_address=get_client_ip(self.request),
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
            ip_address=get_client_ip(request),
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["layout_save_url"] = "#"
        metricas = list(METRICAS_INFO.keys())
        metrics, metricas_info = DashboardMetricsService.get_metrics(
            self.request.user, metricas=metricas
        )
        context["metricas_iter"] = [
            {
                "key": m,
                "data": metrics[m],
                "label": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("label"),
                "icon": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("icon"),
            }
            for m in metricas
            if m in metrics
        ]
        context["metricas_selecionadas"] = metricas
        return context

    def form_valid(self, form):
        layout_data = self.request.POST.get("layout_json", "[]")
        self.object = form.save(self.request.user, layout_data)
        log_layout_action(
            user=self.request.user,
            action="CREATE_LAYOUT",
            layout=self.object,
            ip_address=get_client_ip(self.request),
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
        metrics, metricas_info = DashboardMetricsService.get_metrics(
            self.request.user, metricas=metricas
        )
        context["metricas_iter"] = [
            {
                "key": m,
                "data": metrics[m],
                "label": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("label"),
                "icon": (metricas_info.get(m) or METRICAS_INFO.get(m, {})).get("icon"),
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
            ip_address=get_client_ip(self.request),
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
            ip_address=get_client_ip(request),
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
                ip_address=get_client_ip(request),
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
