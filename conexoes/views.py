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

from accounts.utils import is_htmx_or_ajax

from .forms import ConnectionsSearchForm

User = get_user_model()


def _get_user_connections(user, query: str):
    connections = (
        user.connections.select_related("organizacao", "nucleo")
        if hasattr(user, "connections")
        else User.objects.none()
    )

    if query:
        filters = Q(username__icontains=query) | Q(contato__icontains=query)
        connections = connections.filter(filters)

    return connections


def _get_user_connection_requests(user, query: str):
    connection_requests = (
        user.followers.select_related("organizacao", "nucleo")
        if hasattr(user, "followers")
        else User.objects.none()
    )

    if query:
        filters = Q(username__icontains=query) | Q(contato__icontains=query)
        connection_requests = connection_requests.filter(filters)

    return connection_requests


def _connection_totals(user):
    total_conexoes = user.connections.count() if hasattr(user, "connections") else 0
    total_solicitacoes = user.followers.count() if hasattr(user, "followers") else 0
    total_solicitacoes_enviadas = user.following.count() if hasattr(user, "following") else 0
    return total_conexoes, total_solicitacoes, total_solicitacoes_enviadas


def _build_connections_page_context(request, form, connections, connection_requests, query: str):
    total_conexoes, total_solicitacoes, total_solicitacoes_enviadas = _connection_totals(request.user)
    search_params = {"q": query} if query else {}
    search_page_url = reverse("conexoes:perfil_conexoes_buscar")
    if search_params:
        search_page_url = f"{search_page_url}?{urlencode(search_params)}"

    return {
        "connections": connections,
        "connection_requests": connection_requests,
        "form": form,
        "search_form_action": request.get_full_path(),
        "search_form_hx_get": None,
        "search_form_hx_target": None,
        "search_form_hx_push_url": None,
        "search_page_url": search_page_url,
        "search_page_hx_get": None,
        "search_page_hx_target": None,
        "search_page_hx_push_url": None,
        "total_conexoes": total_conexoes,
        "total_solicitacoes": total_solicitacoes,
        "total_solicitacoes_enviadas": total_solicitacoes_enviadas,
    }


def _build_connection_requests_context(request, query: str = ""):
    connection_requests = _get_user_connection_requests(request.user, query)
    total_conexoes, total_solicitacoes, total_solicitacoes_enviadas = _connection_totals(request.user)

    return {
        "connection_requests": connection_requests,
        "total_conexoes": total_conexoes,
        "total_solicitacoes": total_solicitacoes,
        "total_solicitacoes_enviadas": total_solicitacoes_enviadas,
        "search_page_url": reverse("conexoes:perfil_conexoes_buscar"),
    }


def _profile_dashboard_hx_context():
    return {
        "search_form_hx_get": reverse("conexoes:perfil_conexoes_partial"),
        "search_form_hx_target": "perfil-content",
        "search_form_hx_push_url": "?section=conexoes",
        "search_page_hx_get": reverse("conexoes:perfil_conexoes_buscar"),
        "search_page_hx_target": "perfil-content",
        "search_page_hx_push_url": "?section=conexoes&view=buscar",
    }


def _profile_search_hx_context(query: str):
    params = {"section": "conexoes", "view": "buscar"}
    if query:
        params["q"] = query
    search_push_url = f"?{urlencode(params)}"
    solicitacoes_push_url = "?section=conexoes&tab=solicitacoes"
    solicitacoes_get_url = f"{reverse('conexoes:perfil_conexoes_partial')}?tab=solicitacoes"

    return {
        "search_form_hx_get": reverse("conexoes:perfil_conexoes_buscar"),
        "search_form_hx_target": "perfil-content",
        "search_form_hx_push_url": search_push_url,
        "back_to_dashboard_hx_get": reverse("conexoes:perfil_conexoes_partial"),
        "back_to_dashboard_hx_target": "perfil-content",
        "back_to_dashboard_hx_push_url": "?section=conexoes",
        "solicitacoes_hx_get": solicitacoes_get_url,
        "solicitacoes_hx_target": "perfil-content",
        "solicitacoes_hx_push_url": solicitacoes_push_url,
    }


def _build_search_page_context(request, query: str, form: ConnectionsSearchForm | None):
    context = _build_conexoes_busca_context(request.user, query, form=form)
    dashboard_url = reverse("conexoes:perfil_sections_conexoes")
    total_conexoes, total_solicitacoes, total_solicitacoes_enviadas = _connection_totals(request.user)

    context.update(
        {
            "dashboard_url": dashboard_url,
            "back_to_dashboard_url": dashboard_url,
            "solicitacoes_url": f"{dashboard_url}?tab=solicitacoes",
            "search_form_action": reverse("conexoes:perfil_conexoes_buscar"),
            "search_container_id": "connections-search-card",
            "search_form_hx_get": None,
            "search_form_hx_target": None,
            "search_form_hx_push_url": None,
            "back_to_dashboard_hx_get": None,
            "back_to_dashboard_hx_target": None,
            "back_to_dashboard_hx_push_url": None,
            "solicitacoes_hx_get": None,
            "solicitacoes_hx_target": None,
            "solicitacoes_hx_push_url": None,
            "total_conexoes": total_conexoes,
            "total_solicitacoes": total_solicitacoes,
            "total_solicitacoes_enviadas": total_solicitacoes_enviadas,
        }
    )

    return context


@login_required
def perfil_conexoes(request):
    view_mode = (request.GET.get("view") or "").strip().lower()
    if not is_htmx_or_ajax(request) and view_mode == "buscar":
        params = request.GET.copy()
        params = params.copy()
        params.pop("view", None)
        url = reverse("conexoes:perfil_conexoes_buscar")
        query_string = params.urlencode()
        if query_string:
            url = f"{url}?{query_string}"
        return redirect(url)

    tab = (request.GET.get("tab") or "").strip().lower()
    if tab == "solicitacoes":
        query = (request.GET.get("q") or "").strip()
        context = _build_connection_requests_context(request, query)
        return render(request, "conexoes/solicitacoes.html", context)

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

    connections = _get_user_connections(request.user, q)
    connection_requests = _get_user_connection_requests(request.user, q)
    context = _build_connections_page_context(request, search_form, connections, connection_requests, q)

    if is_htmx_or_ajax(request):
        context.update(_profile_dashboard_hx_context())
        return render(request, "conexoes/partiais/connections_list_content.html", context)

    return render(request, "conexoes/connections_list.html", context)


@login_required
def perfil_conexoes_partial(request):
    if request.method in {"GET", "HEAD"} and not is_htmx_or_ajax(request):
        params = request.GET.copy()
        params = params.copy()
        url = reverse("conexoes:perfil_sections_conexoes")
        query_string = params.urlencode()
        if query_string:
            url = f"{url}?{query_string}"
        return redirect(url)

    username = request.GET.get("username")
    public_id = request.GET.get("public_id")
    if username and username != request.user.username:
        return HttpResponseForbidden(_("Esta seção está disponível apenas para o proprietário do perfil."))
    if public_id and str(request.user.public_id) != public_id:
        return HttpResponseForbidden(_("Esta seção está disponível apenas para o proprietário do perfil."))

    tab = (request.GET.get("tab") or "").strip().lower()
    if tab == "solicitacoes":
        query = (request.GET.get("q") or "").strip()
        context = _build_connection_requests_context(request, query)
        return render(request, "conexoes/partiais/request_list.html", context)

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

    connections = _get_user_connections(request.user, q)
    connection_requests = _get_user_connection_requests(request.user, q)

    context = _build_connections_page_context(request, search_form, connections, connection_requests, q)
    context.update(_profile_dashboard_hx_context())
    return render(request, "conexoes/partiais/connections_list_content.html", context)


@login_required
def perfil_conexoes_buscar(request):
    search_form = ConnectionsSearchForm(
        request.GET or None,
        placeholder=_("Buscar por nome, razão social ou CNPJ..."),
        label=_("Adicionar conexão"),
        aria_label=_("Buscar por nome, razão social ou CNPJ"),
    )
    if search_form.is_valid():
        q = search_form.cleaned_data.get("q", "")
    else:
        q = ""
    context = _build_search_page_context(request, q, search_form)

    if is_htmx_or_ajax(request):
        context.update(_profile_search_hx_context(q))
        context["search_container_id"] = None
        return render(request, "conexoes/partiais/search_card.html", context)

    return render(request, "conexoes/busca.html", context)


def _build_conexoes_busca_context(user, query, form: ConnectionsSearchForm | None = None):
    if form is None:
        form = ConnectionsSearchForm(
            data={"q": query},
            placeholder=_("Buscar por nome, razão social ou CNPJ..."),
            label=_("Adicionar conexão"),
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
        context = _build_search_page_context(request, q, None)
        context.update(_profile_search_hx_context(q))
        context["search_container_id"] = None
        return render(request, "conexoes/partiais/search_card.html", context)

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
            context = _build_search_page_context(request, q, None)
            context.update(_profile_search_hx_context(q))
            context["search_container_id"] = None
            return render(request, "conexoes/partiais/search_card.html", context)
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
