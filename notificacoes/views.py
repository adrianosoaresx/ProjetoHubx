from __future__ import annotations

import csv
import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .forms import NotificationTemplateForm
from .models import (
    Canal,
    Frequencia,
    HistoricoNotificacao,
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
)

logger = logging.getLogger(__name__)


@login_required
@permission_required("notificacoes.change_notificationtemplate", raise_exception=True)
def list_templates(request):
    templates = NotificationTemplate.objects.all()
    return render(request, "notificacoes/templates_list.html", {"templates": templates})


@login_required
@permission_required("notificacoes.add_notificationtemplate", raise_exception=True)
def create_template(request):
    if request.method == "POST":
        form = NotificationTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Template criado com sucesso."))
            return redirect("notificacoes:templates_list")
    else:
        form = NotificationTemplateForm()
    return render(request, "notificacoes/template_form.html", {"form": form})


@login_required
@permission_required("notificacoes.change_notificationtemplate", raise_exception=True)
def edit_template(request, codigo: str):
    template = get_object_or_404(NotificationTemplate, codigo=codigo)
    if request.method == "POST":
        form = NotificationTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, _("Template atualizado com sucesso."))
            return redirect("notificacoes:templates_list")
    else:
        form = NotificationTemplateForm(instance=template)
    return render(request, "notificacoes/template_form.html", {"form": form, "template": template})


@login_required
@staff_member_required
def list_logs(request):
    logs = NotificationLog.objects.select_related("user", "template").order_by("-data_envio")
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")
    canal = request.GET.get("canal")
    status = request.GET.get("status")
    template_codigo = request.GET.get("template")
    if inicio:
        logs = logs.filter(data_envio__date__gte=inicio)
    if fim:
        logs = logs.filter(data_envio__date__lte=fim)
    if canal in Canal.values:
        logs = logs.filter(canal=canal)
    if status in NotificationStatus.values:
        logs = logs.filter(status=status)
    if template_codigo:
        logs = logs.filter(template__codigo=template_codigo)

    if request.GET.get("export") == "csv":
        logger.info("export_logs_view", extra={"user": request.user.id, "count": logs.count()})
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=logs.csv"
        writer = csv.writer(response)
        writer.writerow(["user", "template", "canal", "status", "data_envio", "erro"])
        for log in logs:
            writer.writerow([log.user_id, log.template.codigo, log.canal, log.status, log.data_envio, log.erro])
        return response

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"logs": page_obj}
    template_name = (
        "notificacoes/logs_rows.html" if request.headers.get("HX-Request") else "notificacoes/logs_list.html"
    )
    return render(request, template_name, context)


@login_required
def historico_notificacoes(request):
    historico = HistoricoNotificacao.objects.filter(user=request.user)
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")
    canal = request.GET.get("canal")
    frequencia = request.GET.get("frequencia")
    ordenacao = request.GET.get("ordenacao", "-enviado_em")

    if inicio:
        historico = historico.filter(enviado_em__date__gte=inicio)
    if fim:
        historico = historico.filter(enviado_em__date__lte=fim)
    if canal in Canal.values:
        historico = historico.filter(canal=canal)
    if frequencia in Frequencia.values:
        historico = historico.filter(frequencia=frequencia)
    if ordenacao in ["enviado_em", "-enviado_em"]:
        historico = historico.order_by(ordenacao)

    paginator = Paginator(historico, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"historicos": page_obj}
    template_name = (
        "notificacoes/historico_rows.html" if request.headers.get("HX-Request") else "notificacoes/historico_list.html"
    )
    return render(request, template_name, context)


@login_required
@permission_required("notificacoes.delete_notificationtemplate", raise_exception=True)
def delete_template(request, codigo: str):
    template = get_object_or_404(NotificationTemplate, codigo=codigo)
    if NotificationLog.objects.filter(template=template).exists():
        messages.error(request, _("Template em uso; não é possível removê-lo."))

    else:
        template.delete()
        messages.success(request, _("Template excluído com sucesso."))
    return redirect("notificacoes:templates_list")


@login_required
@staff_member_required
def metrics_dashboard(request):
    logs = NotificationLog.objects.all()
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")
    if inicio:
        logs = logs.filter(created_at__date__gte=inicio)
    if fim:
        logs = logs.filter(created_at__date__lte=fim)
    total_por_canal = {item["canal"]: item["total"] for item in logs.values("canal").annotate(total=Count("id"))}
    falhas_por_canal = {
        item["canal"]: item["total"]
        for item in logs.filter(status=NotificationStatus.FALHA).values("canal").annotate(total=Count("id"))
    }
    context = {
        "total_por_canal": total_por_canal,
        "falhas_por_canal": falhas_por_canal,
        "templates_ativos": NotificationTemplate.objects.count(),
        "templates_inativos": NotificationTemplate.all_objects.filter(deleted=True).count(),
    }
    logger.info("metrics_view", extra={"user": request.user.id})
    return render(request, "notificacoes/metrics.html", context)
