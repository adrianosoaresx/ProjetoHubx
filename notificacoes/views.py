from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.utils import resolve_back_href

from .forms import (
    HistoricoNotificacaoFilterForm,
    NotificationLogFilterForm,
    NotificationTemplateForm,
)
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
@permission_required("notificacoes.view_notificationtemplate", raise_exception=True)
def list_templates(request):
    templates = NotificationTemplate.objects.all().order_by("-created_at")
    paginator = Paginator(templates, 20)
    templates_page = paginator.get_page(request.GET.get("page"))
    context = {
        "templates_page": templates_page,
        "page_obj": templates_page,
    }
    return render(request, "notificacoes/templates_list.html", context)


@login_required
@permission_required("notificacoes.change_notificationtemplate", raise_exception=True)
def toggle_template(request, codigo: str):
    template = get_object_or_404(NotificationTemplate, codigo=codigo)
    if request.method == "POST":
        template.ativo = not template.ativo
        template.save(update_fields=["ativo"])
        if template.ativo:
            messages.success(request, _("Template ativado com sucesso."))
        else:
            messages.success(request, _("Template desativado com sucesso."))
    return redirect("notificacoes:templates_list")


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

    fallback_url = reverse("notificacoes:templates_list")
    back_href = resolve_back_href(request, fallback=fallback_url)
    context = {
        "form": form,
        "back_href": back_href,
        "back_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
        "cancel_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
    }
    return render(request, "notificacoes/template_form.html", context)


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

    fallback_url = reverse("notificacoes:templates_list")
    back_href = resolve_back_href(request, fallback=fallback_url)
    context = {
        "form": form,
        "template": template,
        "back_href": back_href,
        "back_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
        "cancel_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar edição"),
        },
    }
    return render(request, "notificacoes/template_form.html", context)


@login_required
@staff_member_required
def list_logs(request):
    form = NotificationLogFilterForm(request.GET or None)
    logs = NotificationLog.objects.select_related("user", "template").order_by("-data_envio")

    if form.is_valid():
        inicio = form.cleaned_data.get("inicio")
        fim = form.cleaned_data.get("fim")
        canal = form.cleaned_data.get("canal")
        status = form.cleaned_data.get("status")
        template = form.cleaned_data.get("template")

        if inicio:
            logs = logs.filter(data_envio__date__gte=inicio)
        if fim:
            logs = logs.filter(data_envio__date__lte=fim)
        if canal in Canal.values:
            logs = logs.filter(canal=canal)
        if status in NotificationStatus.values:
            logs = logs.filter(status=status)
        if template:
            logs = logs.filter(template=template)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"logs": page_obj, "form": form}
    template_name = (
        "notificacoes/logs_table.html" if request.headers.get("HX-Request") else "notificacoes/logs_list.html"
    )
    return render(request, template_name, context)


@login_required
def historico_notificacoes(request):
    historico = HistoricoNotificacao.objects.filter(user=request.user)
    form = HistoricoNotificacaoFilterForm(request.GET or None)

    if form.is_valid():
        inicio = form.cleaned_data.get("inicio")
        fim = form.cleaned_data.get("fim")
        canal = form.cleaned_data.get("canal")
        frequencia = form.cleaned_data.get("frequencia")
        ordenacao = form.cleaned_data.get("ordenacao") or "-enviado_em"

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
    else:
        historico = historico.order_by("-enviado_em")

    paginator = Paginator(historico, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"historicos": page_obj, "form": form}
    template_name = (
        "notificacoes/historico_table.html" if request.headers.get("HX-Request") else "notificacoes/historico_list.html"
    )
    return render(request, template_name, context)


@login_required
@permission_required("notificacoes.delete_notificationtemplate", raise_exception=True)
def delete_template(request, codigo: str):
    template = get_object_or_404(NotificationTemplate, codigo=codigo)

    if request.method == "POST":
        if NotificationLog.objects.filter(template=template).exists():
            messages.error(
                request,
                _("Template em uso; não é possível removê-lo. Considere desativá-lo."),
            )
        else:
            template.delete()
            messages.success(request, _("Template excluído com sucesso."))
        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("notificacoes:templates_list")
            return response
        return redirect("notificacoes:templates_list")

    fallback_url = reverse("notificacoes:templates_list")
    back_href = resolve_back_href(request, fallback=fallback_url)
    if request.headers.get("HX-Request"):
        form_action = reverse("notificacoes:template_delete", args=[template.codigo])
        modal_context = {
            "template": template,
            "modal_identifier": template.pk or template.codigo,
            "titulo": _("Confirmar exclusão"),
            "mensagem": _("Esta ação não poderá ser desfeita."),
            "pergunta": format_html(
                _("Tem certeza que deseja excluir o template <strong>{codigo}</strong>?"),
                codigo=template.codigo,
            ),
            "submit_label": _("Excluir"),
            "form_action": form_action,
        }
        return render(
            request,
            "notificacoes/partials/template_delete_modal.html",
            modal_context,
        )

    context = {
        "template": template,
        "back_href": back_href,
        "back_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
        "cancel_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar exclusão"),
        },
    }
    return render(
        request,
        "notificacoes/template_confirm_delete.html",
        context,
    )


@login_required
@staff_member_required
def metrics_dashboard(request):
    logs = NotificationLog.objects.filter(data_envio__isnull=False)
    inicio = request.GET.get("inicio")
    fim = request.GET.get("fim")
    if inicio:
        logs = logs.filter(data_envio__date__gte=inicio)
    if fim:
        logs = logs.filter(data_envio__date__lte=fim)
    total_por_canal = {
        item["canal"]: item["total"]
        for item in logs.filter(status=NotificationStatus.ENVIADA).values("canal").annotate(total=Count("id"))
    }
    falhas_por_canal = {
        item["canal"]: item["total"]
        for item in logs.filter(status=NotificationStatus.FALHA).values("canal").annotate(total=Count("id"))
    }
    templates_total = NotificationTemplate.objects.filter(ativo=True).count()
    context = {
        "total_por_canal": total_por_canal,
        "falhas_por_canal": falhas_por_canal,
        "templates_total": templates_total,
    }
    logger.info("metrics_view", extra={"user": request.user.id})
    return render(request, "notificacoes/metrics.html", context)
