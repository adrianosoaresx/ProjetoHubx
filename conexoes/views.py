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

from accounts.models import UserType
from accounts.utils import is_htmx_or_ajax

from .forms import ConnectionsSearchForm

User = get_user_model()

ROOT_CONNECTIONS_FORBIDDEN_MESSAGE = _("Recursos de conexão não estão disponíveis para usuários root.")


def _deny_root_connections_access(request):
    user_type = getattr(request.user, "get_tipo_usuario", None)
    if user_type == UserType.ROOT.value:
        if is_htmx_or_ajax(request):
            return HttpResponseForbidden(ROOT_CONNECTIONS_FORBIDDEN_MESSAGE)
        messages.error(request, ROOT_CONNECTIONS_FORBIDDEN_MESSAGE)
        return redirect("organizacoes:list")
    return None


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


def _get_user_sent_connection_requests(user, query: str):
    sent_requests = (
        user.following.select_related("organizacao", "nucleo")
        if hasattr(user, "following")
        else User.objects.none()
    )

    if query:
        filters = Q(username__icontains=query) | Q(contato__icontains=query)
        sent_requests = sent_requests.filter(filters)

    return sent_requests


def _connection_totals(user):
    total_conexoes = user.connections.count() if hasattr(user, "connections") else 0
    total_solicitacoes = user.followers.count() if hasattr(user, "followers") else 0
    total_solicitacoes_enviadas = user.following.count() if hasattr(user, "following") else 0
    return total_conexoes, total_solicitacoes, total_solicitacoes_enviadas


CONNECTION_FILTER_CHOICES = {"ativas", "pendentes", "enviadas"}


def _resolve_connections_filter(request):
    filter_value = (request.GET.get("filter") or "").strip().lower()
    tab = (request.GET.get("tab") or "").strip().lower()

    if tab == "solicitacoes" and not filter_value:
        filter_value = "pendentes"

    if filter_value not in CONNECTION_FILTER_CHOICES:
        filter_value = "ativas"

    return filter_value


def _build_connections_page_context(
    request,
    form,
    connections,
    connection_requests,
    sent_requests,
    query: str,
    active_filter: str,
    *,
    hx_context: dict[str, str | None] | None = None,
):
    total_conexoes, total_solicitacoes, total_solicitacoes_enviadas = _connection_totals(request.user)
    search_params = {"q": query} if query else {}
    search_page_url = reverse("conexoes:perfil_conexoes_buscar")
    if search_params:
        search_page_url = f"{search_page_url}?{urlencode(search_params)}"

    base_params = request.GET.copy()
    base_params = base_params.copy()
    base_params.pop("tab", None)

    dashboard_url = reverse("conexoes:perfil_sections_conexoes")
    partial_url = reverse("conexoes:perfil_conexoes_partial")

    hx_context = hx_context or {}
    hx_target = hx_context.get("hx_target")
    hx_push_base = hx_context.get("hx_push_base")

    def _build_filter_card(value: str, label: str, icon: str, total: int | None):
        params = base_params.copy()
        params["filter"] = value
        query_string = params.urlencode()
        href = f"{dashboard_url}?{query_string}" if query_string else dashboard_url

        hx_get = None
        hx_push_url = None
        if hx_target:
            hx_get = f"{partial_url}?{query_string}" if query_string else partial_url
        if hx_push_base is not None:
            push_params = params.copy()
            query_push = urlencode(push_params)
            hx_push_url = f"{hx_push_base}{'&' if hx_push_base and query_push else ''}{query_push}" if hx_push_base else f"?{query_push}" if query_push else hx_push_base

        return {
            "label": label,
            "valor": total,
            "icon_name": icon,
            "href": href,
            "is_active": active_filter == value,
            "card_class": "card-compact border border-white/30 bg-white/10 text-white/90 backdrop-blur-sm transition hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70",
            "active_class": "ring-2 ring-white/80 bg-white/20",
            "hx_get": hx_get,
            "hx_target": f"#{hx_target}" if hx_target else None,
            "hx_push_url": hx_push_url,
        }

    filter_cards = [
        _build_filter_card("ativas", _("Conexões ativas"), "users", total_conexoes),
        _build_filter_card("pendentes", _("Solicitações pendentes"), "user-check", total_solicitacoes),
        _build_filter_card("enviadas", _("Solicitações enviadas"), "user-plus", total_solicitacoes_enviadas),
    ]

    return {
        "connections": connections,
        "connection_requests": connection_requests,
        "sent_requests": sent_requests,
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
        "connections_filter": active_filter,
        "connection_filter_cards": filter_cards,
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
    solicitacoes_push_url = "?section=conexoes&filter=pendentes"
    solicitacoes_get_url = f"{reverse('conexoes:perfil_conexoes_partial')}?filter=pendentes"

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
            "solicitacoes_url": f"{dashboard_url}?filter=pendentes",
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
    response = _deny_root_connections_access(request)
    if response:
        return response
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

    active_filter = _resolve_connections_filter(request)

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
    sent_requests = _get_user_sent_connection_requests(request.user, q)
    context = _build_connections_page_context(
        request,
        search_form,
        connections,
        connection_requests,
        sent_requests,
        q,
        active_filter,
    )

    if is_htmx_or_ajax(request):
        context.update(_profile_dashboard_hx_context())
        return render(request, "conexoes/partiais/connections_list_content.html", context)

    return render(request, "conexoes/connections_list.html", context)


@login_required
def perfil_conexoes_partial(request):
    response = _deny_root_connections_access(request)
    if response:
        return response
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

    active_filter = _resolve_connections_filter(request)

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
    sent_requests = _get_user_sent_connection_requests(request.user, q)

    context = _build_connections_page_context(
        request,
        search_form,
        connections,
        connection_requests,
        sent_requests,
        q,
        active_filter,
        hx_context={
            "hx_target": "perfil-content",
            "hx_push_base": "?section=conexoes",
        },
    )
    context.update(_profile_dashboard_hx_context())
    return render(request, "conexoes/partiais/connections_list_content.html", context)


@login_required
def perfil_conexoes_buscar(request):
    response = _deny_root_connections_access(request)
    if response:
        return response
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

    response = _deny_root_connections_access(request)
    if response:
        return response

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

    response = _deny_root_connections_access(request)
    if response:
        return response
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

    response = _deny_root_connections_access(request)
    if response:
        return response
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
    return redirect(f"{reverse('conexoes:perfil_sections_conexoes')}?filter=pendentes")


@login_required
def recusar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    response = _deny_root_connections_access(request)
    if response:
        return response
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
    return redirect(f"{reverse('conexoes:perfil_sections_conexoes')}?filter=pendentes")
