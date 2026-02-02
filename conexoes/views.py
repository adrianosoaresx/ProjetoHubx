import json
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import F, Q, Value
from django.db.models.functions import Replace
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views import View

from accounts.models import UserType
from accounts.utils import is_htmx_or_ajax
from notificacoes.services.notificacoes import enviar_para_usuario

from .forms import ConnectionsSearchForm

User = get_user_model()

ROOT_CONNECTIONS_FORBIDDEN_MESSAGE = _("Recursos de conexão não estão disponíveis para usuários root.")
GUEST_CONNECTIONS_FORBIDDEN_MESSAGE = _("Recursos de conexão não estão disponíveis para usuários convidados.")
CONNECTION_NOTIFICATION_TEMPLATES = {
    "request": "connection_request",
    "accepted": "connection_accepted",
    "declined": "connection_declined",
}
CONNECTIONS_REFRESH_TRIGGER = json.dumps({"conexoes:refresh": True})


def _get_display_name(user):
    name = getattr(user, "get_display_name", lambda: None)() or user.get_full_name()
    if name:
        return name
    return getattr(user, "username", str(user))


def _deny_root_connections_access(request):
    user_type = getattr(request.user, "get_tipo_usuario", None) or getattr(request.user, "user_type", None)
    if isinstance(user_type, UserType):
        user_type = user_type.value

    if user_type == UserType.ROOT.value:
        message = ROOT_CONNECTIONS_FORBIDDEN_MESSAGE
    elif user_type == UserType.CONVIDADO.value:
        message = GUEST_CONNECTIONS_FORBIDDEN_MESSAGE
    else:
        return None

    if is_htmx_or_ajax(request):
        return HttpResponseForbidden(message)
    messages.error(request, message)
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
CONEXOES_CAROUSEL_PAGE_SIZE = 6


def _resolve_connections_filter(request):
    status_value = (request.GET.get("status") or "").strip().lower()
    filter_value = (request.GET.get("filter") or "").strip().lower()
    tab = (request.GET.get("tab") or "").strip().lower()

    resolved = status_value or filter_value

    if tab == "solicitacoes" and not resolved:
        resolved = "pendentes"

    if resolved not in CONNECTION_FILTER_CHOICES:
        resolved = "ativas"

    return resolved


def _get_connections_search_form(request):
    form = ConnectionsSearchForm(
        request.GET or None,
        placeholder=_("Buscar conexões..."),
        label=_("Buscar conexões"),
        aria_label=_("Buscar conexões"),
    )
    if form.is_valid():
        query = form.cleaned_data.get("q", "") or ""
    else:
        query = ""
    return form, query.strip()


def _build_connections_refresh_url(request):
    params = request.GET.copy()
    refresh_url = reverse("conexoes:perfil_conexoes_partial")
    query_string = params.urlencode()
    if query_string:
        refresh_url = f"{refresh_url}?{query_string}"
    return refresh_url


def _htmx_refresh_response(*, status: int = 204, redirect_url: str | None = None):
    response = HttpResponse(status=status)
    response["HX-Trigger"] = CONNECTIONS_REFRESH_TRIGGER
    if redirect_url:
        response["HX-Redirect"] = redirect_url
    return response


def _build_connections_page_context(
    request,
    form,
    connections,
    connection_requests,
    sent_requests,
    query: str,
    active_filter: str,
    *,
    section_pages: dict[str, int] | None = None,
):
    if section_pages is None:
        section_pages = {}

    total_conexoes, total_solicitacoes, total_solicitacoes_enviadas = _connection_totals(request.user)
    search_params = {"q": query} if query else {}
    search_page_url = reverse("conexoes:perfil_conexoes_buscar")
    if search_params:
        search_page_url = f"{search_page_url}?{urlencode(search_params)}"

    carousel_sections = build_conexao_carousel_sections(
        request,
        connections=connections,
        connection_requests=connection_requests,
        sent_requests=sent_requests,
        search_term=query,
        status_filter=active_filter,
        section_pages=section_pages,
    )

    sections = carousel_sections.get("sections", {})

    def get_section(section_key: str):
        return sections.get(section_key, {})

    minhas_section = get_section("minhas")
    pendentes_section = get_section("pendentes")
    enviadas_section = get_section("enviadas")

    context = {
        "connections": connections,
        "connection_requests": connection_requests,
        "sent_requests": sent_requests,
        "form": form,
        "connections_refresh_url": _build_connections_refresh_url(request),
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
        "conexoes_carousel_fetch_url": carousel_sections.get("fetch_url"),
        "conexoes_search_query": carousel_sections.get("search_term", ""),
        "conexoes_status_filter": carousel_sections.get("status_filter", ""),
        "minhas_conexoes_page": minhas_section.get("page_obj"),
        "minhas_conexoes_empty_message": minhas_section.get("empty_message"),
        "minhas_conexoes_empty_cta": None,
        "minhas_conexoes_aria_label": minhas_section.get("aria_label"),
        "solicitacoes_pendentes_page": pendentes_section.get("page_obj"),
        "solicitacoes_pendentes_empty_message": pendentes_section.get("empty_message"),
        "solicitacoes_pendentes_empty_cta": None,
        "solicitacoes_pendentes_aria_label": pendentes_section.get("aria_label"),
        "solicitacoes_enviadas_page": enviadas_section.get("page_obj"),
        "solicitacoes_enviadas_empty_message": enviadas_section.get("empty_message"),
        "solicitacoes_enviadas_empty_cta": None,
        "solicitacoes_enviadas_aria_label": enviadas_section.get("aria_label"),
    }

    _refresh_minhas_conexoes_empty_cta(context)

    return context


def _refresh_minhas_conexoes_empty_cta(context):
    search_page_url = context.get("search_page_url")
    if not search_page_url:
        context["minhas_conexoes_empty_cta"] = None
        return

    context["minhas_conexoes_empty_cta"] = {
        "label": _("Buscar Pessoas"),
        "href": search_page_url,
        "hx_get": context.get("search_page_hx_get"),
        "hx_target": context.get("search_page_hx_target"),
        "hx_push_url": context.get("search_page_hx_push_url"),
    }


def build_conexao_carousel_sections(
    request,
    *,
    connections,
    connection_requests,
    sent_requests,
    search_term: str | None = None,
    status_filter: str | None = None,
    section_pages: dict[str, int] | None = None,
    only_sections: set[str] | None = None,
):
    if section_pages is None:
        section_pages = {}

    if search_term is None:
        search_term = (request.GET.get("q") or "").strip()

    if status_filter is None:
        status_filter = _resolve_connections_filter(request)

    fetch_url = reverse("conexoes:conexoes_carousel_api")

    section_definitions = {
        "minhas": {
            "queryset": connections if connections is not None else User.objects.none(),
            "empty_message": _("Você ainda não tem conexões."),
            "aria_label": _("Lista de conexões ativas"),
        },
        "pendentes": {
            "queryset": connection_requests if connection_requests is not None else User.objects.none(),
            "empty_message": _("Você não tem solicitações de conexão pendentes."),
            "aria_label": _("Lista de solicitações de conexão pendentes"),
        },
        "enviadas": {
            "queryset": sent_requests if sent_requests is not None else User.objects.none(),
            "empty_message": _("Você não enviou solicitações de conexão recentemente."),
            "aria_label": _("Lista de solicitações de conexão enviadas"),
        },
    }

    sections: dict[str, dict[str, object]] = {}

    for section_key, definition in section_definitions.items():
        if only_sections is not None and section_key not in only_sections:
            continue

        queryset = definition["queryset"]
        paginator = Paginator(queryset, CONEXOES_CAROUSEL_PAGE_SIZE)
        page_number = section_pages.get(section_key) or 1
        page_obj = paginator.get_page(page_number)

        sections[section_key] = {
            "section": section_key,
            "page_obj": page_obj,
            "paginator": paginator,
            "total": paginator.count,
            "total_pages": paginator.num_pages,
            "empty_message": definition["empty_message"],
            "aria_label": definition["aria_label"],
            "fetch_url": fetch_url,
            "search_term": search_term,
            "status_filter": status_filter,
        }

    return {
        "sections": sections,
        "fetch_url": fetch_url,
        "search_term": search_term,
        "status_filter": status_filter,
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


def _build_search_page_context(
    request, query: str, form: ConnectionsSearchForm | None, *, page_number: int | None = None
):
    if page_number is None:
        try:
            page_number = int(request.GET.get("page") or 1)
        except (TypeError, ValueError):
            page_number = 1
    if page_number < 1:
        page_number = 1

    context = _build_conexoes_busca_context(
        request.user, query, form=form, page_number=page_number
    )
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
            "membros_carousel_fetch_url": reverse("conexoes:conexoes_busca_carousel_api"),
            "membros_aria_label": _("Resultados da busca de conexões"),
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

    tab = (request.GET.get("tab") or "").strip().lower()
    active_filter = _resolve_connections_filter(request)

    search_form, q = _get_connections_search_form(request)

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
        if tab == "solicitacoes":
            return render(request, "conexoes/partiais/request_list.html", context)
        return render(request, "conexoes/partiais/connections_list_content.html", context)

    if tab == "solicitacoes":
        return render(request, "conexoes/solicitacoes.html", context)

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

    tab = (request.GET.get("tab") or "").strip().lower()
    active_filter = _resolve_connections_filter(request)

    search_form, q = _get_connections_search_form(request)

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
    context.update(_profile_dashboard_hx_context())
    _refresh_minhas_conexoes_empty_cta(context)
    if tab == "solicitacoes":
        return render(request, "conexoes/partiais/request_list.html", context)
    return render(request, "conexoes/partiais/connections_list_content.html", context)


class ConexaoListCarouselView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = _deny_root_connections_access(request)
        if response:
            return response

        section = (request.GET.get("section") or "minhas").strip().lower()
        valid_sections = {"minhas", "pendentes", "enviadas"}
        if section not in valid_sections:
            return JsonResponse({"error": _("Seção inválida.")}, status=400)

        try:
            page_number = int(request.GET.get("page") or 1)
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1

        search_form, search_term = _get_connections_search_form(request)
        status_filter = _resolve_connections_filter(request)

        connections = _get_user_connections(request.user, search_term)
        connection_requests = _get_user_connection_requests(request.user, search_term)
        sent_requests = _get_user_sent_connection_requests(request.user, search_term)

        base_context = _build_connections_page_context(
            request,
            search_form,
            connections,
            connection_requests,
            sent_requests,
            search_term,
            status_filter,
            section_pages={section: page_number},
        )

        section_context_map = {
            "minhas": {
                "page": "minhas_conexoes_page",
                "empty_message": "minhas_conexoes_empty_message",
                "empty_cta": "minhas_conexoes_empty_cta",
            },
            "pendentes": {
                "page": "solicitacoes_pendentes_page",
                "empty_message": "solicitacoes_pendentes_empty_message",
                "empty_cta": "solicitacoes_pendentes_empty_cta",
            },
            "enviadas": {
                "page": "solicitacoes_enviadas_page",
                "empty_message": "solicitacoes_enviadas_empty_message",
                "empty_cta": "solicitacoes_enviadas_empty_cta",
            },
        }

        mapping = section_context_map.get(section)
        page_obj = base_context.get(mapping["page"])
        if page_obj is None:
            return JsonResponse({"error": _("Seção não disponível.")}, status=404)

        empty_message = base_context.get(mapping["empty_message"])
        empty_cta = base_context.get(mapping["empty_cta"])

        html = render_to_string(
            "conexoes/partials/conexao_carousel_slide.html",
            {
                "items": page_obj.object_list,
                "page_number": page_obj.number,
                "section": section,
                "empty_message": empty_message,
                "empty_cta": empty_cta,
            },
            request=request,
        )

        paginator = getattr(page_obj, "paginator", None)
        total_pages = paginator.num_pages if paginator else 1
        total_count = paginator.count if paginator else len(page_obj.object_list)

        return JsonResponse(
            {
                "html": html,
                "page": page_obj.number,
                "total_pages": total_pages,
                "count": total_count,
            }
        )


class ConexaoBuscaCarouselView(LoginRequiredMixin, View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        response = _deny_root_connections_access(request)
        if response:
            return response

        try:
            page_number = int(request.GET.get("page") or 1)
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1

        search_form = ConnectionsSearchForm(
            request.GET or None,
            placeholder=_("Buscar por nome, razão social ou CNPJ..."),
            label=_("Adicionar conexão"),
            aria_label=_("Buscar por nome, razão social ou CNPJ"),
        )
        if search_form.is_valid():
            query = search_form.cleaned_data.get("q", "")
        else:
            query = ""

        base_context = _build_search_page_context(
            request, query, search_form, page_number=page_number
        )
        page_obj = base_context.get("membros_page")
        if page_obj is None:
            return JsonResponse({"error": _("Seção não disponível.")}, status=404)

        html = render_to_string(
            "conexoes/partials/conexao_busca_carousel_slide.html",
            {
                **base_context,
                "items": getattr(page_obj, "object_list", []),
                "page_number": getattr(page_obj, "number", 1),
                "empty_message": base_context.get("membros_empty_message"),
            },
            request=request,
        )

        paginator = getattr(page_obj, "paginator", None)
        total_pages = paginator.num_pages if paginator else 1
        total_count = paginator.count if paginator else len(getattr(page_obj, "object_list", []))

        return JsonResponse(
            {
                "html": html,
                "page": getattr(page_obj, "number", 1),
                "total_pages": total_pages,
                "count": total_count,
            }
        )


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


def _build_conexoes_busca_context(
    user,
    query,
    form: ConnectionsSearchForm | None = None,
    *,
    page_number: int = 1,
):
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

    membros = User.objects.none()

    if organizacao:
        membros = (
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
            membros = membros.filter(filters)

        membros = membros.order_by("nome_fantasia", "contato", "username")

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

    try:
        parsed_page = int(page_number)
    except (TypeError, ValueError):
        parsed_page = 1
    if parsed_page < 1:
        parsed_page = 1

    paginator = Paginator(membros, CONEXOES_CAROUSEL_PAGE_SIZE)
    page_obj = paginator.get_page(parsed_page)

    empty_message = _("Nenhum membro encontrado para os critérios informados.")
    if not organizacao:
        empty_message = _("Você não está vinculado a uma organização no momento.")

    return {
        "membros": membros,
        "membros_page": page_obj,
        "membros_empty_message": empty_message,
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
    elif request.user.followers.filter(id=other_user.id).exists():
        request.user.connections.add(other_user)
        request.user.followers.remove(other_user)
        if other_user.followers.filter(id=request.user.id).exists():
            other_user.followers.remove(request.user)
        messages.success(
            request,
            _("Conexão com %(nome)s aceita.")
            % {"nome": _get_display_name(other_user)},
        )
        enviar_para_usuario(
            other_user,
            CONNECTION_NOTIFICATION_TEMPLATES["accepted"],
            {
                "solicitado": _get_display_name(request.user),
                "actor_id": str(request.user.id),
            },
        )
    elif other_user.followers.filter(id=request.user.id).exists():
        messages.info(request, _("Solicitação de conexão já enviada."))
    else:
        other_user.followers.add(request.user)
        messages.success(request, _("Solicitação de conexão enviada."))
        enviar_para_usuario(
            other_user,
            CONNECTION_NOTIFICATION_TEMPLATES["request"],
            {
                "solicitante": _get_display_name(request.user),
                "actor_id": str(request.user.id),
            },
        )

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
def remover_conexao_modal(request, id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    response = _deny_root_connections_access(request)
    if response:
        return response

    if not is_htmx_or_ajax(request):
        return redirect("conexoes:perfil_sections_conexoes")

    connection = get_object_or_404(User, id=id)
    target_id = (request.GET.get("target_id") or "").strip()
    swap = (request.GET.get("swap") or "").strip()
    remove_target = (request.GET.get("remove_target") or "").strip()
    query = (request.GET.get("q") or "").strip()

    def _normalize_target(value: str) -> str | None:
        if not value:
            return None
        if value.startswith("#") or value.startswith("."):
            return value
        return f"#{value}"

    hx_target = _normalize_target(target_id)
    hx_swap = swap or None
    remove_selector = _normalize_target(remove_target)

    display_name = connection.display_name or connection.get_full_name() or connection.username

    context = {
        "connection": connection,
        "titulo": _("Remover conexão"),
        "mensagem": format_html(
            _("Tem certeza que deseja remover a conexão com <strong>{nome}</strong>?"),
            nome=display_name,
        ),
        "submit_label": _("Remover"),
        "form_action": reverse("conexoes:remover_conexao", args=[connection.id]),
        "hx_target": hx_target,
        "hx_swap": hx_swap,
        "remove_target": remove_selector,
        "query": query,
    }

    return render(request, "conexoes/partiais/remove_connection_modal.html", context)


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
        return _htmx_refresh_response()
    return redirect("conexoes:perfil_sections_conexoes")


@login_required
def aceitar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    response = _deny_root_connections_access(request)
    if response:
        return response
    redirect_url = f"{reverse('conexoes:perfil_sections_conexoes')}?filter=pendentes"
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        if is_htmx_or_ajax(request):
            return _htmx_refresh_response(status=404, redirect_url=redirect_url)
        return redirect(redirect_url)

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        if is_htmx_or_ajax(request):
            return _htmx_refresh_response(status=404, redirect_url=redirect_url)
        return redirect(redirect_url)

    request.user.connections.add(other_user)
    request.user.followers.remove(other_user)
    messages.success(request, f"Conexão com {other_user.get_full_name()} aceita.")
    enviar_para_usuario(
        other_user,
        CONNECTION_NOTIFICATION_TEMPLATES["accepted"],
        {
            "solicitado": _get_display_name(request.user),
            "actor_id": str(request.user.id),
        },
    )
    if is_htmx_or_ajax(request):
        return _htmx_refresh_response()
    return redirect(redirect_url)


@login_required
def recusar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    response = _deny_root_connections_access(request)
    if response:
        return response
    redirect_url = f"{reverse('conexoes:perfil_sections_conexoes')}?filter=pendentes"
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        if is_htmx_or_ajax(request):
            return _htmx_refresh_response(status=404, redirect_url=redirect_url)
        return redirect(redirect_url)

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        if is_htmx_or_ajax(request):
            return _htmx_refresh_response(status=404, redirect_url=redirect_url)
        return redirect(redirect_url)

    request.user.followers.remove(other_user)
    messages.success(request, f"Solicitação de conexão de {other_user.get_full_name()} recusada.")
    enviar_para_usuario(
        other_user,
        CONNECTION_NOTIFICATION_TEMPLATES["declined"],
        {
            "solicitado": _get_display_name(request.user),
            "actor_id": str(request.user.id),
        },
    )
    if is_htmx_or_ajax(request):
        return _htmx_refresh_response()
    return redirect(redirect_url)
