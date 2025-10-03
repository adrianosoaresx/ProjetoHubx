import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Value
from django.db.models.functions import Replace
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from accounts.utils import is_htmx_or_ajax, redirect_to_profile_section

from .forms import ConnectionsSearchForm

User = get_user_model()


def _connection_lists_for_user(user, query: str):
    connections = (
        user.connections.select_related("organizacao", "nucleo")
        if hasattr(user, "connections")
        else User.objects.none()
    )
    connection_requests = (
        user.followers.select_related("organizacao", "nucleo")
        if hasattr(user, "followers")
        else User.objects.none()
    )

    if query:
        filters = Q(username__icontains=query) | Q(contato__icontains=query)
        connections = connections.filter(filters)
        connection_requests = connection_requests.filter(filters)

    return connections, connection_requests


@login_required
def perfil_conexoes(request):
    if request.method in {"GET", "HEAD"} and not is_htmx_or_ajax(request):
        return redirect_to_profile_section(request, "conexoes")

    tab = request.GET.get("tab", "minhas").lower()
    search_form = ConnectionsSearchForm(
        request.GET or None,
        placeholder=_("Buscar conexões..."),
        label=_("Buscar conexões"),
        aria_label=_("Buscar conexões"),
    )
    if search_form.is_valid():
        q = search_form.cleaned_data.get("q", "")
    else:
        q = ""

    connections, connection_requests = _connection_lists_for_user(request.user, q)

    template_map = {
        "solicitacoes": "perfil/partials/conexoes_solicitacoes.html",
        "minhas": "perfil/partials/conexoes_minhas.html",
    }
    template_name = template_map.get(tab, template_map["minhas"])

    context = {
        "connections": connections,
        "connection_requests": connection_requests,
        "q": q,
        "form": search_form,
    }
    return render(request, template_name, context)


@login_required
def perfil_conexoes_partial(request):
    if request.method in {"GET", "HEAD"} and not is_htmx_or_ajax(request):
        return redirect_to_profile_section(request, "conexoes")

    username = request.GET.get("username")
    public_id = request.GET.get("public_id")
    if username and username != request.user.username:
        return HttpResponseForbidden(_("Esta seção está disponível apenas para o proprietário do perfil."))
    if public_id and str(request.user.public_id) != public_id:
        return HttpResponseForbidden(_("Esta seção está disponível apenas para o proprietário do perfil."))

    search_form = ConnectionsSearchForm(
        request.GET or None,
        placeholder=_("Buscar conexões..."),
        label=_("Buscar conexões"),
        aria_label=_("Buscar conexões"),
    )
    if search_form.is_valid():
        q = search_form.cleaned_data.get("q", "")
    else:
        q = ""

    connections, connection_requests = _connection_lists_for_user(request.user, q)

    context = {
        "connections": connections,
        "connection_requests": connection_requests,
        "q": q,
        "form": search_form,
    }
    return render(request, "perfil/partials/conexoes_dashboard.html", context)


@login_required
def perfil_conexoes_buscar(request):
    if request.method in {"GET", "HEAD"} and not is_htmx_or_ajax(request):
        return redirect_to_profile_section(request, "conexoes")

    search_form = ConnectionsSearchForm(
        request.GET or None,
        placeholder=_("Buscar por nome, razão social ou CNPJ..."),
        label=_("Buscar pessoas"),
        aria_label=_("Buscar por nome, razão social ou CNPJ"),
    )
    if search_form.is_valid():
        q = search_form.cleaned_data.get("q", "")
    else:
        q = ""
    context = _build_conexoes_busca_context(request.user, q, form=search_form)
    return render(request, "perfil/partials/conexoes_busca.html", context)


def _build_conexoes_busca_context(user, query, form: ConnectionsSearchForm | None = None):
    if form is None:
        form = ConnectionsSearchForm(
            data={"q": query},
            placeholder=_("Buscar por nome, razão social ou CNPJ..."),
            label=_("Buscar pessoas"),
            aria_label=_("Buscar por nome, razão social ou CNPJ"),
        )
        if form.is_valid():
            query = form.cleaned_data.get("q", "")
        else:
            query = ""
    else:
        if form.is_valid():
            query = form.cleaned_data.get("q", "")
        else:
            query = ""
    organizacao = getattr(user, "organizacao", None)

    associados = User.objects.none()

    if organizacao:
        associados = (
            User.objects.filter(organizacao=organizacao, is_associado=True)
            .exclude(pk=user.pk)
            .select_related("organizacao", "nucleo")
            .annotate(
                cnpj_digits=Replace(
                    Replace(
                        Replace(Replace(F("cnpj"), Value("."), Value("")), Value("-"), Value("")),
                        Value("/"),
                        Value(""),
                    ),
                    Value(" "),
                    Value(""),
                )
            )
        )

        if query:
            digits = re.sub(r"\D", "", query)
            filters = (
                Q(contato__icontains=query)
                | Q(nome_fantasia__icontains=query)
                | Q(username__icontains=query)
                | Q(razao_social__icontains=query)
                | Q(cnpj__icontains=query)
            )
            if digits:
                filters |= Q(cnpj_digits__icontains=digits)
            associados = associados.filter(filters)

        associados = associados.order_by("nome_fantasia", "contato", "username")

    conexoes_ids = set()
    solicitacoes_enviadas_ids = set()
    solicitacoes_recebidas_ids = set()

    if hasattr(user, "connections"):
        conexoes_ids = set(user.connections.values_list("id", flat=True))
    if hasattr(user, "following"):
        solicitacoes_enviadas_ids = set(user.following.values_list("id", flat=True))
    if hasattr(user, "followers"):
        solicitacoes_recebidas_ids = set(user.followers.values_list("id", flat=True))

    if conexoes_ids:
        solicitacoes_enviadas_ids -= conexoes_ids
        solicitacoes_recebidas_ids -= conexoes_ids

    return {
        "associados": associados,
        "q": query,
        "tem_organizacao": bool(organizacao),
        "conexoes_ids": conexoes_ids,
        "solicitacoes_enviadas_ids": solicitacoes_enviadas_ids,
        "solicitacoes_recebidas_ids": solicitacoes_recebidas_ids,
        "form": form,
    }


@login_required
def solicitar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    other_user = get_object_or_404(User, id=id)

    if other_user == request.user:
        messages.error(request, _("Você não pode conectar-se consigo mesmo."))
    elif request.user.connections.filter(id=other_user.id).exists():
        messages.info(request, _("Vocês já estão conectados."))
    elif other_user.followers.filter(id=request.user.id).exists():
        messages.info(request, _("Solicitação de conexão já enviada."))
    else:
        other_user.followers.add(request.user)
        messages.success(request, _("Solicitação de conexão enviada."))

    q = request.POST.get("q", "").strip()

    if is_htmx_or_ajax(request):
        context = _build_conexoes_busca_context(request.user, q)
        return render(request, "perfil/partials/conexoes_busca.html", context)

    params = {"section": "conexoes", "view": "buscar"}
    if q:
        params["q"] = q
    return redirect(f"{reverse('conexoes:perfil_sections_conexoes')}?{urlencode(params)}")


@login_required
def remover_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        other_user = User.objects.get(id=id)
        request.user.connections.remove(other_user)
        messages.success(request, f"Conexão com {other_user.get_full_name()} removida.")
    except User.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
    q = request.POST.get("q", "").strip()
    if is_htmx_or_ajax(request):
        hx_target = request.headers.get("HX-Target", "")
        if hx_target == "perfil-content":
            context = _build_conexoes_busca_context(request.user, q)
            return render(request, "perfil/partials/conexoes_busca.html", context)
        return HttpResponse(status=204)
    return redirect("conexoes:perfil_sections_conexoes")


@login_required
def aceitar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("conexoes:perfil_sections_conexoes")

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("conexoes:perfil_sections_conexoes")

    request.user.connections.add(other_user)
    request.user.followers.remove(other_user)
    messages.success(request, f"Conexão com {other_user.get_full_name()} aceita.")
    if is_htmx_or_ajax(request):
        return HttpResponse(status=204)
    return redirect(f"{reverse('conexoes:perfil_sections_conexoes')}?tab=solicitacoes")


@login_required
def recusar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("conexoes:perfil_sections_conexoes")

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("conexoes:perfil_sections_conexoes")

    request.user.followers.remove(other_user)
    messages.success(request, f"Solicitação de conexão de {other_user.get_full_name()} recusada.")
    if is_htmx_or_ajax(request):
        return HttpResponse(status=204)
    return redirect(f"{reverse('conexoes:perfil_sections_conexoes')}?tab=solicitacoes")
