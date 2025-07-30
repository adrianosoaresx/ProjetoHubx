from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import NotificationTemplateForm, UserNotificationPreferenceForm
from .models import Canal, NotificationLog, NotificationStatus, NotificationTemplate, UserNotificationPreference


@login_required
@permission_required("notificacoes.change_notificationtemplate", raise_exception=True)
def list_templates(request):
    templates = NotificationTemplate.objects.all()
    return render(request, "notificacoes/templates_list.html", {"templates": templates})


@login_required
@permission_required("notificacoes.change_notificationtemplate", raise_exception=True)
def create_template(request):
    if request.method == "POST":
        form = NotificationTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Template criado com sucesso.")
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
            messages.success(request, "Template atualizado com sucesso.")
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
    if inicio:
        logs = logs.filter(data_envio__date__gte=inicio)
    if fim:
        logs = logs.filter(data_envio__date__lte=fim)
    if canal in Canal.values:
        logs = logs.filter(canal=canal)
    if status in NotificationStatus.values:
        logs = logs.filter(status=status)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"logs": page_obj}
    if request.headers.get("HX-Request"):
        context["partial"] = True
    return render(request, "notificacoes/logs_list.html", context)


@login_required
def editar_preferencias(request):
    pref, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserNotificationPreferenceForm(request.POST, instance=pref)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferências salvas com sucesso.")
            return redirect("notificacoes:editar_preferencias")
    else:
        form = UserNotificationPreferenceForm(instance=pref)
    return render(request, "notificacoes/preferencias.html", {"form": form})
