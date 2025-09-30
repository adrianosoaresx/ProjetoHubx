import os
import re
import uuid
from pathlib import Path

from django.conf import settings
import json
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile, File
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import F, Prefetch, Q, Value
from django.db.models.functions import Lower, Replace
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET
from django.views.generic import FormView, ListView, TemplateView
from urllib.parse import urlencode
from django_ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.serializers import UserSerializer
from accounts.tasks import (
    send_cancel_delete_email,
    send_confirmation_email,
    send_password_reset_email,
)
from core.permissions import (
    AssociadosRequiredMixin,
    IsAdmin,
    IsCoordenador,
    NoSuperadminMixin,
)
from nucleos.models import ConviteNucleo, Nucleo, ParticipacaoNucleo
from tokens.models import TokenAcesso
from tokens.utils import get_client_ip
from .forms import (
    EmailLoginForm,
    InformacoesPessoaisForm,
    MediaForm,
    OrganizacaoUserCreateForm,
)
from .models import AccountToken, SecurityEvent, UserMedia, UserType
from .validators import cpf_validator

User = get_user_model()

# Alias for compatibility with newer media query helpers
Midia = UserMedia


PERFIL_DEFAULT_SECTION = "portfolio"
PERFIL_SECTION_URLS = {
    "portfolio": "accounts:perfil_portfolio",
    "info": "accounts:perfil_info_partial",
}

PERFIL_OWNER_SECTION_URLS = {
    **PERFIL_SECTION_URLS,
    "conexoes": "accounts:perfil_conexoes_partial",
}


def _is_htmx_or_ajax(request) -> bool:
    """Return whether the request was triggered via HTMX or XMLHttpRequest."""

    if request.headers.get("HX-Request"):
        return True
    requested_with = request.headers.get("X-Requested-With", "")
    return isinstance(requested_with, str) and requested_with.lower() == "xmlhttprequest"


def _redirect_to_profile_section(request, section: str, extra_params: dict[str, str | None] | None = None):
    params = request.GET.copy()
    params = params.copy()
    if extra_params:
        for key, value in extra_params.items():
            if value is None:
                params.pop(key, None)
            else:
                params[key] = value
    params["section"] = section
    query_string = params.urlencode()
    url = reverse("accounts:perfil")
    if query_string:
        url = f"{url}?{query_string}"
    return redirect(url)


def _resolve_back_url(request, default: str | None = None) -> str:
    """Return a safe back URL for profile partial views."""

    allowed_hosts = {request.get_host()}
    candidates = [
        request.headers.get("HX-Current-URL"),
        request.META.get("HTTP_REFERER"),
        default,
    ]

    if default is None:
        candidates.append(reverse("accounts:perfil"))

    for candidate in candidates:
        if candidate and url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts=allowed_hosts,
            require_https=request.is_secure(),
        ):
            return candidate

    return reverse("accounts:perfil")


def _perfil_default_section_url(request, *, allow_owner_sections: bool = False):
    allowed_sections = PERFIL_OWNER_SECTION_URLS if allow_owner_sections else PERFIL_SECTION_URLS

    section = (request.GET.get("section") or "").strip().lower()
    if section not in allowed_sections:
        section = PERFIL_DEFAULT_SECTION

    params = request.GET.copy()
    params = params.copy()
    params.pop("section", None)

    url_name = allowed_sections[section]
    url_args: list[str] = []

    if allow_owner_sections:
        if section == "portfolio":
            view_mode = params.get("portfolio_view")
            media_pk = params.get("media")
            section_views = {
                "detail": "accounts:perfil_sections_portfolio_detail",
                "edit": "accounts:perfil_sections_portfolio_edit",
                "delete": "accounts:perfil_sections_portfolio_delete",
            }
            selected_view = section_views.get(view_mode)
            if selected_view and media_pk:
                url_name = selected_view
                url_args = [media_pk]
                params.pop("portfolio_view", None)
                params.pop("media", None)
        elif section == "info" and params.get("info_view") == "edit":
            url_name = "accounts:perfil_sections_info"
            params.pop("info_view", None)

    url = reverse(url_name, args=url_args)
    query_string = params.urlencode()
    if query_string:
        url = f"{url}?{query_string}"

    return section, url


def _portfolio_for(profile, viewer, limit: int = 6):
    """Return up to ``limit`` recent media visible to ``viewer`` for ``profile``.

    Falls back to a simple ownership filter if a custom ``visible_to``
    manager method is not available.
    """

    owner_field = "owner" if any(f.name == "owner" for f in Midia._meta.get_fields()) else "user"
    visible = getattr(Midia.objects, "visible_to", None)
    if callable(visible):
        qs = visible(viewer, profile)
    else:
        qs = Midia.objects.filter(**{owner_field: profile})

    return list(qs.select_related(owner_field).prefetch_related("tags").order_by("-created_at")[:limit])


def _profile_hero_names(profile):
    display_name = profile.display_name
    contact_name = profile.contact_name
    subtitle = contact_name if contact_name and contact_name != display_name else ""
    return display_name, subtitle


def _resolve_profile_for_partial(request):
    """Return the profile for partial requests enforcing visibility rules."""

    username = request.GET.get("username")
    public_id = request.GET.get("public_id")
    pk = request.GET.get("pk")
    viewer = request.user if request.user.is_authenticated else None

    if username or public_id or pk:
        filters = {}
        if public_id:
            filters["public_id"] = public_id
        elif pk:
            filters["pk"] = pk
        else:
            filters["username"] = username
        profile = get_object_or_404(User, **filters)
        is_owner = viewer == profile
        if not profile.perfil_publico and not is_owner:
            return None, None, HttpResponseForbidden()
    else:
        if not viewer:
            return None, None, HttpResponseForbidden()
        profile = viewer
        is_owner = True

    return profile, is_owner, None


def _can_manage_profile(viewer, profile) -> bool:
    if viewer is None or not getattr(viewer, "is_authenticated", False):
        return False
    if viewer == profile:
        return True

    viewer_type = getattr(viewer, "get_tipo_usuario", None)
    if viewer_type == UserType.ROOT.value:
        return True

    if viewer_type in {UserType.ADMIN.value, UserType.OPERADOR.value}:
        viewer_org = getattr(viewer, "organizacao_id", None)
        profile_org = getattr(profile, "organizacao_id", None)
        return viewer_org is not None and viewer_org == profile_org

    return False


def _resolve_management_target_user(request):
    viewer = request.user
    if not getattr(viewer, "is_authenticated", False):
        raise PermissionDenied

    target = viewer
    lookup_candidates = (
        (request.POST, ("public_id", "public_id")),
        (request.POST, ("username", "username")),
        (request.POST, ("user_id", "pk")),
        (request.POST, ("pk", "pk")),
        (request.GET, ("public_id", "public_id")),
        (request.GET, ("username", "username")),
        (request.GET, ("user_id", "pk")),
        (request.GET, ("pk", "pk")),
    )

    for params, (param, field) in lookup_candidates:
        value = params.get(param)
        if value:
            try:
                target = get_object_or_404(User, **{field: value})
            except (TypeError, ValueError):
                raise Http404
            break

    if not _can_manage_profile(viewer, target):
        raise PermissionDenied

    return target


# ====================== PERFIL ======================


@login_required
def perfil(request):
    """Exibe a página de perfil privado do usuário."""

    viewer = request.user
    target_user = viewer
    is_owner = True

    lookup_params = ("public_id", "username", "pk", "user_id")
    if any(request.GET.get(param) for param in lookup_params):
        target_user = _resolve_management_target_user(request)
        is_owner = target_user == viewer

    if not getattr(target_user, "is_authenticated", False):
        raise PermissionDenied

    portfolio_recent = _portfolio_for(target_user, request.user, limit=6)
    hero_title, hero_subtitle = _profile_hero_names(target_user)

    allow_owner_sections = _can_manage_profile(viewer, target_user)

    context = {
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "profile": target_user,
        "is_owner": is_owner,
        "portfolio_recent": portfolio_recent,
        "portfolio_form": MediaForm() if allow_owner_sections else None,
        "portfolio_show_form": False,
        "portfolio_q": "",
    }

    default_section, default_url = _perfil_default_section_url(
        request, allow_owner_sections=allow_owner_sections
    )
    context.update(
        {
            "perfil_default_section": default_section,
            "perfil_default_url": default_url,
        }
    )

    return render(request, "perfil/perfil.html", context)


def perfil_publico(request, pk=None, public_id=None, username=None):
    if public_id:
        perfil = get_object_or_404(User, public_id=public_id, perfil_publico=True)
    elif pk:
        perfil = get_object_or_404(User, pk=pk, perfil_publico=True)
    else:
        perfil = get_object_or_404(User, username=username, perfil_publico=True)

    if request.user == perfil:
        return redirect("accounts:perfil")
    portfolio_recent = _portfolio_for(perfil, request.user, limit=6)
    hero_title, hero_subtitle = _profile_hero_names(perfil)

    context = {
        "perfil": perfil,
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "is_owner": request.user == perfil,
        "portfolio_recent": portfolio_recent,
        "portfolio_form": None,
        "portfolio_show_form": False,
        "portfolio_q": "",
    }

    default_section, default_url = _perfil_default_section_url(request)
    context.update(
        {
            "perfil_default_section": default_section,
            "perfil_default_url": default_url,
        }
    )

    return render(request, "perfil/publico.html", context)


@require_GET
def perfil_section(request, section):
    profile, is_owner, error = _resolve_profile_for_partial(request)
    if error:
        return error

    viewer = request.user if request.user.is_authenticated else None
    context: dict[str, object] = {
        "profile": profile,
        "is_owner": is_owner,
    }

    can_manage = _can_manage_profile(viewer, profile) if viewer else False
    context["can_manage"] = can_manage

    if section == "portfolio":
        q = request.GET.get("q", "").strip()
        medias_qs = (
            Midia.objects.visible_to(viewer, profile)
            .select_related("user")
            .prefetch_related("tags")
            .order_by("-created_at")
        )
        if q:
            medias_qs = medias_qs.filter(Q(descricao__icontains=q) | Q(tags__nome__icontains=q)).distinct()

        show_form = is_owner and request.GET.get("adicionar") == "1"
        form = MediaForm() if is_owner else None
        if form is not None:
            allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
            form.fields["file"].widget.attrs["accept"] = ",".join(allowed_exts)
            form.fields["file"].help_text = _("Selecione um arquivo")
            form.fields["descricao"].help_text = _("Breve descrição do portfólio")

        context.update(
            {
                "medias": medias_qs,
                "form": form,
                "show_form": show_form,
                "q": q,
                "back_url": _resolve_back_url(request),
            }
        )
        template = "perfil/partials/portfolio.html"

    elif section == "info":
        if can_manage:
            bio = getattr(profile, "biografia", "") or getattr(profile, "bio", "")
            context.update(
                {
                    "user": profile,
                    "bio": bio,
                    "manage_target_public_id": profile.public_id,
                    "manage_target_username": profile.username,
                }
            )
            template = "perfil/partials/detail_informacoes.html"
        else:
            template = "perfil/partials/publico_informacoes.html"

    elif section == "conexoes":
        if not is_owner:
            return HttpResponseForbidden(_("Esta seção está disponível apenas para o proprietário do perfil."))

        q = request.GET.get("q", "").strip()
        connections = (
            profile.connections.select_related("organizacao", "nucleo")
            if hasattr(profile, "connections")
            else User.objects.none()
        )
        connection_requests = (
            profile.followers.select_related("organizacao", "nucleo")
            if hasattr(profile, "followers")
            else User.objects.none()
        )
        if q:
            filters = Q(username__icontains=q) | Q(contato__icontains=q)
            connections = connections.filter(filters)
            connection_requests = connection_requests.filter(filters)

        context.update(
            {
                "connections": connections,
                "connection_requests": connection_requests,
                "q": q,
            }
        )
        template = "perfil/partials/conexoes_dashboard.html"

    else:
        return HttpResponseBadRequest("Invalid section")

    return render(request, template, context)


@login_required
def perfil_info(request):
    target_user = _resolve_management_target_user(request)
    is_self = target_user == request.user

    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        extra_params: dict[str, str | None] | None = {"info_view": "edit"}
        if not is_self:
            extra_params.update(
                {
                    "public_id": str(target_user.public_id),
                    "username": target_user.username,
                }
            )
        return _redirect_to_profile_section(request, "info", extra_params)

    if request.method == "POST":
        form = InformacoesPessoaisForm(request.POST, request.FILES, instance=target_user)
        if form.is_valid():
            form.save()
            if getattr(form, "email_changed", False):
                if is_self:
                    messages.info(request, _("Confirme o novo e-mail enviado."))
                else:
                    messages.info(request, _("O usuário deverá confirmar o novo e-mail enviado."))
            else:
                if is_self:
                    messages.success(request, _("Informações do perfil atualizadas."))
                else:
                    messages.success(
                        request,
                        _("Informações do perfil de %(username)s atualizadas.")
                        % {"username": target_user.get_full_name()},
                    )

            extra_params: dict[str, str | None] | None = {"info_view": None}
            if not is_self:
                extra_params.update(
                    {
                        "public_id": str(target_user.public_id),
                        "username": target_user.username,
                    }
                )
            return _redirect_to_profile_section(request, "info", extra_params)
    else:
        form = InformacoesPessoaisForm(instance=target_user)

    return render(
        request,
        "perfil/partials/info_form.html",
        {
            "form": form,
            "target_user": target_user,
            "is_self": is_self,
        },
    )


@login_required
def perfil_notificacoes(request):
    """Redireciona para a aba de preferências centralizada em ConfiguracaoConta."""
    return redirect("configuracoes:configuracoes")


@ratelimit(key="ip", rate="5/m", method="GET", block=True)
def check_2fa(request):
    """Return neutral response without revealing 2FA status or email existence."""
    return HttpResponse(status=204)


@login_required
def perfil_conexoes(request):
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        return _redirect_to_profile_section(request, "conexoes")

    q = request.GET.get("q", "").strip()
    tab = request.GET.get("tab", "minhas").lower()
    connections = (
        request.user.connections.select_related("organizacao", "nucleo")
        if hasattr(request.user, "connections")
        else User.objects.none()
    )
    connection_requests = (
        request.user.followers.select_related("organizacao", "nucleo")
        if hasattr(request.user, "followers")
        else User.objects.none()
    )

    if q:
        filters = Q(username__icontains=q) | Q(contato__icontains=q)
        connections = connections.filter(filters)
        connection_requests = connection_requests.filter(filters)

    template_map = {
        "solicitacoes": "perfil/partials/conexoes_solicitacoes.html",
        "minhas": "perfil/partials/conexoes_minhas.html",
    }
    template_name = template_map.get(tab, template_map["minhas"])

    context = {
        "connections": connections,
        "connection_requests": connection_requests,
        "q": q,
    }
    return render(request, template_name, context)


@login_required
def perfil_conexoes_buscar(request):
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        return _redirect_to_profile_section(request, "conexoes")

    q = request.GET.get("q", "").strip()
    organizacao = getattr(request.user, "organizacao", None)

    associados = User.objects.none()

    if organizacao:
        associados = (
            User.objects.filter(organizacao=organizacao, is_associado=True)
            .exclude(pk=request.user.pk)
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

        if q:
            digits = re.sub(r"\D", "", q)
            filters = (
                Q(contato__icontains=q)
                | Q(nome_fantasia__icontains=q)
                | Q(username__icontains=q)
                | Q(razao_social__icontains=q)
                | Q(cnpj__icontains=q)
            )
            if digits:
                filters |= Q(cnpj_digits__icontains=digits)
            associados = associados.filter(filters)

        associados = associados.order_by("nome_fantasia", "contato", "username")

    context = {
        "associados": associados,
        "q": q,
        "tem_organizacao": bool(organizacao),
    }

    return render(request, "perfil/partials/conexoes_busca.html", context)


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
    if _is_htmx_or_ajax(request):
        return HttpResponse(status=204)
    return redirect("accounts:perfil_sections_conexoes")


@login_required
def aceitar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:perfil_sections_conexoes")

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:perfil_sections_conexoes")

    request.user.connections.add(other_user)
    request.user.followers.remove(other_user)
    messages.success(request, f"Conexão com {other_user.get_full_name()} aceita.")
    if _is_htmx_or_ajax(request):
        return HttpResponse(status=204)
    return redirect(f"{reverse('accounts:perfil_sections_conexoes')}?tab=solicitacoes")


@login_required
def recusar_conexao(request, id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:perfil_sections_conexoes")

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:perfil_sections_conexoes")

    request.user.followers.remove(other_user)
    messages.success(request, f"Solicitação de conexão de {other_user.get_full_name()} recusada.")
    if _is_htmx_or_ajax(request):
        return HttpResponse(status=204)
    return redirect(f"{reverse('accounts:perfil_sections_conexoes')}?tab=solicitacoes")


@login_required
def perfil_portfolio(request):
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        return _redirect_to_profile_section(request, "portfolio")

    show_form = request.GET.get("adicionar") == "1" or request.method == "POST"
    q = request.GET.get("q", "").strip()

    if request.method == "POST":
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.user = request.user
            media.save()
            form.save_m2m()
            messages.success(request, "Arquivo enviado com sucesso.")
            return _redirect_to_profile_section(request, "portfolio")
    else:
        form = MediaForm()

    allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
    form.fields["file"].widget.attrs["accept"] = ",".join(allowed_exts)
    form.fields["file"].help_text = _("Selecione um arquivo")
    form.fields["descricao"].help_text = _("Breve descrição do portfólio")

    medias_qs = request.user.medias.select_related("user").prefetch_related("tags").order_by("-created_at")
    if q:
        medias_qs = medias_qs.filter(Q(descricao__icontains=q) | Q(tags__nome__icontains=q)).distinct()

    medias = medias_qs

    return render(
        request,
        "perfil/partials/portfolio.html",
        {
            "form": form,
            "medias": medias,
            "show_form": show_form,
            "q": q,
            "is_owner": True,
            "back_url": _resolve_back_url(request),
        },
    )


@login_required
def perfil_portfolio_detail(request, pk):
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        return _redirect_to_profile_section(
            request,
            "portfolio",
            {"portfolio_view": "detail", "media": str(pk)},
        )

    media = get_object_or_404(UserMedia, pk=pk, user=request.user)
    return render(request, "perfil/partials/portfolio_detail.html", {"media": media})


@login_required
def perfil_portfolio_edit(request, pk):
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        return _redirect_to_profile_section(
            request,
            "portfolio",
            {"portfolio_view": "edit", "media": str(pk)},
        )

    media = get_object_or_404(UserMedia, pk=pk, user=request.user)
    if request.method == "POST":
        form = MediaForm(request.POST, request.FILES, instance=media)
        if form.is_valid():
            form.save()
            messages.success(request, "Portfólio atualizado com sucesso.")
            return _redirect_to_profile_section(request, "portfolio")
    else:
        form = MediaForm(instance=media)

    allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
    form.fields["file"].widget.attrs["accept"] = ",".join(allowed_exts)
    form.fields["file"].help_text = _("Selecione um arquivo")
    form.fields["descricao"].help_text = _("Breve descrição do portfólio")

    return render(request, "perfil/partials/portfolio_form.html", {"form": form})


@login_required
def perfil_portfolio_delete(request, pk):
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        return _redirect_to_profile_section(
            request,
            "portfolio",
            {"portfolio_view": "delete", "media": str(pk)},
        )

    media = get_object_or_404(UserMedia, pk=pk, user=request.user)
    if request.method == "POST":
        media.delete(soft=False)
        messages.success(request, "Item do portfólio removido.")
        return _redirect_to_profile_section(request, "portfolio")
    return render(request, "perfil/partials/portfolio_confirm_delete.html", {"media": media})


# ====================== AUTENTICAÇÃO ======================


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:perfil")

    form = EmailLoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            totp=form.cleaned_data.get("totp"),
        )
        if user and user.is_active:
            login(request, user)
            return redirect("accounts:perfil")
        if user and not user.is_active:
            messages.error(request, _("Conta inativa. Verifique seu e-mail para ativá-la."))
        else:
            messages.error(request, _("Credenciais inválidas."))

    return render(request, "login/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


def conta_inativa(request):
    """Exibe aviso para usuários inativos e encerra a sessão."""
    if request.user.is_authenticated:
        logout(request)
    return render(request, "account_inactive.html")


@login_required
def excluir_conta(request):
    """Permite que o usuário exclua sua própria conta."""

    target_user = _resolve_management_target_user(request)
    is_self = target_user == request.user

    def _redirect_to_form():
        url = reverse("accounts:excluir_conta")
        if not is_self:
            params = urlencode(
                {
                    "public_id": str(target_user.public_id),
                    "username": target_user.username,
                }
            )
            url = f"{url}?{params}"
        return redirect(url)

    if request.method == "GET":
        return render(
            request,
            "accounts/delete_account_confirm.html",
            {"target_user": target_user, "is_self": is_self},
        )

    if request.method != "POST":
        return _redirect_to_form()

    if request.POST.get("confirm") != "EXCLUIR":
        messages.error(request, _("Confirme digitando EXCLUIR."))
        return _redirect_to_form()

    with transaction.atomic():
        user = target_user
        user.delete()
        user.exclusao_confirmada = True
        user.is_active = False
        user.save(update_fields=["exclusao_confirmada", "is_active"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="conta_excluida",
            ip=get_client_ip(request),
        )
        token = AccountToken.objects.create(
            usuario=user,
            tipo=AccountToken.Tipo.CANCEL_DELETE,
            expires_at=timezone.now() + timezone.timedelta(days=30),
            ip_gerado=get_client_ip(request),
        )

    send_cancel_delete_email.delay(token.id)

    if is_self:
        logout(request)
        messages.success(
            request,
            _("Sua conta foi excluída com sucesso. Você pode reativá-la em até 30 dias."),
        )
        return redirect("core:home")

    messages.success(
        request,
        _("Conta de %(username)s excluída com sucesso.")
        % {"username": target_user.get_full_name()},
    )
    return redirect("accounts:associados_lista")


@ratelimit(key="ip", rate="5/h", method="POST", block=True)
def password_reset(request):
    """Solicita redefinição de senha."""
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:  # pragma: no cover - feedback uniforme
                pass
            else:
                AccountToken.objects.filter(
                    usuario=user,
                    tipo=AccountToken.Tipo.PASSWORD_RESET,
                    used_at__isnull=True,
                ).update(used_at=timezone.now())
                token = AccountToken.objects.create(
                    usuario=user,
                    tipo=AccountToken.Tipo.PASSWORD_RESET,
                    expires_at=timezone.now() + timezone.timedelta(hours=1),
                    ip_gerado=get_client_ip(request),
                )
                SecurityEvent.objects.create(
                    usuario=user,
                    evento="senha_reset_solicitada",
                    ip=get_client_ip(request),
                )
                send_password_reset_email.delay(token.id)
        messages.success(
            request,
            _("Se o e-mail estiver cadastrado, enviaremos instru\u00e7\u00f5es."),
        )
        return redirect("accounts:password_reset")

    return render(request, "accounts/password_reset.html")


def password_reset_confirm(request, code: str):
    """Define nova senha a partir de um token."""
    token = get_object_or_404(
        AccountToken,
        codigo=code,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
    )
    if token.expires_at < timezone.now() or token.used_at:
        SecurityEvent.objects.create(
            usuario=token.usuario,
            evento="senha_redefinicao_falha",
            ip=get_client_ip(request),
        )
        messages.error(request, _("Token inv\u00e1lido ou expirado."))
        return redirect("accounts:password_reset")

    if request.method == "POST":
        form = SetPasswordForm(token.usuario, request.POST)
        if form.is_valid():
            form.save()
            user = token.usuario
            cache.delete(f"failed_login_attempts_user_{user.pk}")
            cache.delete(f"lockout_user_{user.pk}")
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])
            SecurityEvent.objects.create(
                usuario=user,
                evento="senha_redefinida",
                ip=get_client_ip(request),
            )
            messages.success(request, _("Senha redefinida com sucesso."))
            return redirect("accounts:login")
    else:
        form = SetPasswordForm(token.usuario)

    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"form": form},
    )


def confirmar_email(request, token: str):
    """Valida token de confirmação de e-mail."""
    try:
        token_obj = AccountToken.objects.select_related("usuario").get(
            codigo=token,
            tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        )
    except AccountToken.DoesNotExist:
        return render(request, "accounts/email_confirm.html", {"status": "erro"})

    if token_obj.expires_at < timezone.now() or token_obj.used_at:
        SecurityEvent.objects.create(
            usuario=token_obj.usuario,
            evento="email_confirmacao_falha",
            ip=get_client_ip(request),
        )
        return render(request, "accounts/email_confirm.html", {"status": "erro"})

    with transaction.atomic():
        user = token_obj.usuario
        user.is_active = True
        user.email_confirmed = True
        user.save(update_fields=["is_active", "email_confirmed"])
        token_obj.used_at = timezone.now()
        token_obj.save(update_fields=["used_at"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="email_confirmado",
            ip=get_client_ip(request),
        )
    return render(request, "accounts/email_confirm.html", {"status": "sucesso"})


def onboarding(request):
    return render(request, "register/onboarding.html")


def cancel_delete(request, token: str):
    """Reativa a conta utilizando um token de cancelamento."""
    try:
        token_obj = AccountToken.objects.select_related("usuario").get(
            codigo=token,
            tipo=AccountToken.Tipo.CANCEL_DELETE,
        )
    except AccountToken.DoesNotExist:
        return render(request, "accounts/cancel_delete.html", {"status": "erro"})

    if token_obj.expires_at < timezone.now() or token_obj.used_at:
        return render(request, "accounts/cancel_delete.html", {"status": "erro"})

    with transaction.atomic():
        user = token_obj.usuario
        user.deleted = False
        user.deleted_at = None
        user.is_active = True
        user.exclusao_confirmada = False
        user.save(update_fields=["deleted", "deleted_at", "is_active", "exclusao_confirmada"])
        token_obj.used_at = timezone.now()
        token_obj.save(update_fields=["used_at"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="cancelou_exclusao",
            ip=get_client_ip(request),
        )

    return render(request, "accounts/cancel_delete.html", {"status": "sucesso"})


@ratelimit(key="ip", rate="5/h", method="POST", block=True)
def resend_confirmation(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            try:
                user = User.objects.get(
                    email__iexact=email,
                    is_active=False,
                    deleted=False,
                )
            except User.DoesNotExist:
                pass
            else:
                AccountToken.objects.filter(
                    usuario=user,
                    tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                    used_at__isnull=True,
                ).update(used_at=timezone.now())
                token = AccountToken.objects.create(
                    usuario=user,
                    tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                    expires_at=timezone.now() + timezone.timedelta(hours=24),
                    ip_gerado=get_client_ip(request),
                )
                send_confirmation_email.delay(token.id)
                SecurityEvent.objects.create(
                    usuario=user,
                    evento="resend_confirmation",
                    ip=get_client_ip(request),
                )
        messages.success(
            request,
            _("Se o e-mail estiver cadastrado, enviaremos nova confirmação."),
        )
        return redirect("accounts:login")
    return render(request, "accounts/resend_confirmation.html")


# ====================== REGISTRO MULTIETAPAS ======================


def nome(request):
    if request.method == "POST":
        nome_val = request.POST.get("nome")
        if nome_val:
            request.session["nome"] = nome_val
            return redirect("accounts:cpf")
    return render(request, "register/nome.html")


def cpf(request):
    if request.method == "POST":
        valor = request.POST.get("cpf")
        if valor:
            try:
                cpf_validator(valor)
                if User.objects.filter(cpf=valor).exists():
                    messages.error(request, _("CPF já cadastrado."))
                    return redirect("accounts:cpf")
                else:
                    request.session["cpf"] = valor
                    return redirect("accounts:email")
            except ValidationError:
                messages.error(request, "CPF inválido.")
    return render(request, "register/cpf.html")


def email(request):
    if request.method == "POST":
        val = request.POST.get("email")
        if val:
            if User.objects.filter(email__iexact=val).exists():
                messages.error(request, _("Este e-mail já está em uso."))
                return redirect("accounts:email")
            else:
                request.session["email"] = val
                return redirect("accounts:senha")
    return render(request, "register/email.html")


def usuario(request):
    if request.method == "POST":
        usr = request.POST.get("usuario")
        if usr:
            if User.objects.filter(username__iexact=usr).exists():
                messages.error(request, _("Nome de usuário já cadastrado."))
                return redirect("accounts:usuario")
            else:
                request.session["usuario"] = usr
                return redirect("accounts:nome")
    return render(request, "register/usuario.html")


def senha(request):
    if request.method == "POST":
        s1 = request.POST.get("senha")
        s2 = request.POST.get("confirmar_senha")
        if s1 and s1 == s2:
            try:
                validate_password(s1)
            except ValidationError as exc:
                for msg in exc.messages:
                    messages.error(request, msg)
            else:
                request.session["senha_hash"] = make_password(s1)
                return redirect("accounts:foto")
    return render(request, "register/senha.html")


def foto(request):
    if request.method == "POST":
        arquivo = request.FILES.get("foto")
        if arquivo:
            ext = Path(arquivo.name).suffix.lower()
            allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
            max_size = getattr(settings, "USER_MEDIA_MAX_SIZE", 50 * 1024 * 1024)
            if ext not in allowed_exts:
                messages.error(request, _("Formato de arquivo não permitido."))
                return redirect("accounts:foto")
            if arquivo.size > max_size:
                messages.error(request, _("Arquivo excede o tamanho máximo permitido."))
                return redirect("accounts:foto")
            temp_name = f"temp/{uuid.uuid4()}_{arquivo.name}"
            path = default_storage.save(temp_name, ContentFile(arquivo.read()))
            request.session["foto"] = path
            return redirect("accounts:termos")
        return redirect("accounts:foto")
    return render(request, "register/foto.html")


def termos(request):
    if request.method == "POST" and request.POST.get("aceitar_termos"):
        token_code = request.session.get("invite_token")
        try:
            token_obj = TokenAcesso.objects.get(codigo=token_code, estado=TokenAcesso.Estado.NOVO)
        except TokenAcesso.DoesNotExist:
            messages.error(request, "Token inválido.")
            return redirect("tokens:token")
        if token_obj.data_expiracao < timezone.now():
            token_obj.estado = TokenAcesso.Estado.EXPIRADO
            token_obj.save(update_fields=["estado"])
            messages.error(request, "Token expirado.")
            return redirect("tokens:token")

        username = request.session.get("usuario")
        email_val = request.session.get("email")
        pwd_hash = request.session.get("senha_hash")
        cpf_val = request.session.get("cpf")
        contato = (request.session.get("nome") or "").strip()

        if username and pwd_hash:
            if token_obj.tipo_destino != TokenAcesso.TipoUsuario.CONVIDADO:
                messages.error(request, _("Convite inválido."))
                return redirect("tokens:token")
            mapped_user_type = UserType.CONVIDADO
            try:
                with transaction.atomic():
                    user = User.objects.create(
                        username=username,
                        email=email_val,
                        contato=contato,
                        password=pwd_hash,
                        cpf=cpf_val,
                        user_type=mapped_user_type,
                        is_active=False,
                        email_confirmed=False,
                    )
            except IntegrityError:
                messages.error(
                    request,
                    _("Nome de usuário já cadastrado."),
                )
                request.session.pop("usuario", None)
                return redirect("accounts:usuario")

            convite_nucleo = ConviteNucleo.objects.select_related("nucleo").filter(token_obj=token_obj).first()
            if convite_nucleo and convite_nucleo.nucleo_id:
                user.nucleo = convite_nucleo.nucleo
                user.save(update_fields=["nucleo"])
            foto_path = request.session.get("foto")
            if foto_path:
                with default_storage.open(foto_path, "rb") as f:
                    user.avatar.save(os.path.basename(foto_path), File(f))
                default_storage.delete(foto_path)
                del request.session["foto"]

            token_obj.estado = TokenAcesso.Estado.USADO
            token_obj.save(update_fields=["estado"])

            token = AccountToken.objects.create(
                usuario=user,
                tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                expires_at=timezone.now() + timezone.timedelta(hours=24),
                ip_gerado=get_client_ip(request),
            )
            send_confirmation_email.delay(token.id)

            request.session["termos"] = True
            return redirect("accounts:registro_sucesso")

        messages.error(request, "Erro ao criar usuário. Tente novamente.")
        return redirect("accounts:usuario")

    return render(request, "register/termos.html")


def registro_sucesso(request):
    return render(request, "register/registro_sucesso.html")


class OrganizacaoUserCreateView(NoSuperadminMixin, LoginRequiredMixin, FormView):
    template_name = "associados/usuario_form.html"
    form_class = OrganizacaoUserCreateForm
    success_url = reverse_lazy("accounts:associados_lista")

    def dispatch(self, request, *args, **kwargs):
        allowed_types = self.get_allowed_user_types()
        if not allowed_types or getattr(request.user, "organizacao_id", None) is None:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_allowed_user_types(self) -> list[str]:
        tipo_usuario = getattr(self.request.user, "get_tipo_usuario", None)
        if tipo_usuario in {UserType.ADMIN.value, UserType.ROOT.value}:
            return [UserType.ASSOCIADO.value, UserType.OPERADOR.value]
        if tipo_usuario == UserType.OPERADOR.value:
            return [UserType.ASSOCIADO.value]
        return []

    def get_initial(self):
        initial = super().get_initial()
        requested_type = self.request.GET.get("tipo")
        if requested_type in self.get_allowed_user_types():
            initial["user_type"] = requested_type
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["allowed_user_types"] = self.get_allowed_user_types()
        return kwargs

    def form_valid(self, form):
        organizacao = getattr(self.request.user, "organizacao", None)
        if organizacao is None:
            raise PermissionDenied

        new_user = form.save(organizacao=organizacao)
        type_labels = {value: label for value, label in UserType.choices}
        tipo_display = type_labels.get(new_user.user_type, new_user.user_type)
        messages.success(
            self.request,
            _("Usuário %(username)s (%(tipo)s) adicionado com sucesso.")
            % {
                "username": new_user.get_full_name(),
                "tipo": tipo_display,
            },
        )
        return super().form_valid(form)


class AssociadoListView(NoSuperadminMixin, AssociadosRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "associados/associado_list.html"
    context_object_name = "associados"
    paginate_by = 10

    def get_queryset(self):
        User = get_user_model()
        org = self.request.user.organizacao
        qs = (
            User.objects.filter(organizacao=org)
            .filter(
                Q(is_associado=True)
                | Q(
                    user_type__in=[
                        UserType.NUCLEADO.value,
                        UserType.COORDENADOR.value,
                        UserType.CONSULTOR.value,
                    ]
                )
                | Q(is_coordenador=True)
            )
            .select_related("organizacao", "nucleo")
            .prefetch_related("participacoes__nucleo", "nucleos_consultoria")
        )
        # TODO: unify "user_type" and "is_associado" fields to avoid duplicate state
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(contato__icontains=q))

        filtro_tipo = self.request.GET.get("tipo")
        consultor_filter = Q(user_type=UserType.CONSULTOR.value)
        coordenador_filter = (
            Q(user_type=UserType.COORDENADOR.value)
            | Q(is_coordenador=True)
            | Q(
                participacoes__papel="coordenador",
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            )
        )
        if filtro_tipo == "associados":
            qs = qs.filter(is_associado=True, nucleo__isnull=True)
        elif filtro_tipo == "nucleados":
            qs = qs.filter(is_associado=True, nucleo__isnull=False)
        elif filtro_tipo == "consultores":
            qs = qs.filter(consultor_filter)
        elif filtro_tipo == "coordenadores":
            qs = qs.filter(coordenador_filter)

        qs = qs.distinct()

        # Ordenação alfabética por username (case-insensitive)
        qs = qs.annotate(_user=Lower("username"))
        return qs.order_by("_user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        valid_filters = {"associados", "nucleados", "consultores", "coordenadores"}
        current_filter = self.request.GET.get("tipo") or ""
        if current_filter not in valid_filters:
            current_filter = "todos"

        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")

        def build_url(filter_value: str | None) -> str:
            query_params = params.copy()
            if filter_value in valid_filters:
                query_params["tipo"] = filter_value
            else:
                query_params.pop("tipo", None)
            query_string = query_params.urlencode()
            return f"{self.request.path}?{query_string}" if query_string else self.request.path

        context["current_filter"] = current_filter
        context["associados_filter_url"] = build_url("associados")
        context["nucleados_filter_url"] = build_url("nucleados")
        context["consultores_filter_url"] = build_url("consultores")
        context["coordenadores_filter_url"] = build_url("coordenadores")
        context["todos_filter_url"] = build_url(None)
        context["is_associados_filter_active"] = current_filter == "associados"
        context["is_nucleados_filter_active"] = current_filter == "nucleados"
        context["is_consultores_filter_active"] = current_filter == "consultores"
        context["is_coordenadores_filter_active"] = current_filter == "coordenadores"

        org = getattr(self.request.user, "organizacao", None)
        if org:
            # Totais por organização
            context["total_usuarios"] = User.objects.filter(organizacao=org).count()
            # Associados sem vínculo a núcleo
            context["total_associados"] = User.objects.filter(
                organizacao=org, is_associado=True, nucleo__isnull=True
            ).count()
            # Nucleados (inclui coordenadores vinculados a um núcleo)
            context["total_nucleados"] = User.objects.filter(
                organizacao=org, is_associado=True, nucleo__isnull=False
            ).count()
            consultor_filter = Q(user_type=UserType.CONSULTOR.value)
            context["total_consultores"] = (
                User.objects.filter(organizacao=org).filter(consultor_filter).distinct().count()
            )
            coordenador_filter = (
                Q(user_type=UserType.COORDENADOR.value)
                | Q(is_coordenador=True)
                | Q(
                    participacoes__papel="coordenador",
                    participacoes__status="ativo",
                    participacoes__status_suspensao=False,
                )
            )
            context["total_coordenadores"] = (
                User.objects.filter(organizacao=org).filter(coordenador_filter).distinct().count()
            )
        else:
            context["total_usuarios"] = 0
            context["total_associados"] = 0
            context["total_nucleados"] = 0
            context["total_consultores"] = 0
            context["total_coordenadores"] = 0
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template="associados/_grid.html",
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )
        return super().render_to_response(context, **response_kwargs)


class AssociadoPromoverListView(NoSuperadminMixin, AssociadosRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "associados/promover_list.html"
    context_object_name = "associados"
    paginate_by = 12

    def get_queryset(self):
        User = get_user_model()
        organizacao = getattr(self.request.user, "organizacao", None)
        self.organizacao = organizacao
        if organizacao is None:
            self.search_term = ""
            return User.objects.none()

        base_queryset = (
            User.objects.filter(organizacao=organizacao)
            .filter(
                Q(
                    user_type__in=[
                        UserType.COORDENADOR.value,
                        UserType.CONSULTOR.value,
                        UserType.ASSOCIADO.value,
                        UserType.NUCLEADO.value,
                    ]
                )
                | Q(is_associado=True)
                | Q(is_coordenador=True)
            )
            .select_related("organizacao", "nucleo")
            .prefetch_related("participacoes__nucleo", "nucleos_consultoria")
        )

        search_term = (self.request.GET.get("q") or "").strip()
        self.search_term = search_term

        if search_term:
            base_queryset = base_queryset.filter(
                Q(username__icontains=search_term)
                | Q(contato__icontains=search_term)
                | Q(nome_fantasia__icontains=search_term)
                | Q(razao_social__icontains=search_term)
                | Q(cnpj__icontains=search_term)
            )

        consultor_filter = Q(user_type=UserType.CONSULTOR.value)
        coordenador_filter = (
            Q(user_type=UserType.COORDENADOR.value)
            | Q(is_coordenador=True)
            | Q(
                participacoes__papel="coordenador",
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            )
        )

        filtro_tipo = self.request.GET.get("tipo")
        if filtro_tipo == "associados":
            base_queryset = base_queryset.filter(is_associado=True, nucleo__isnull=True)
        elif filtro_tipo == "nucleados":
            base_queryset = base_queryset.filter(is_associado=True, nucleo__isnull=False)
        elif filtro_tipo == "consultores":
            base_queryset = base_queryset.filter(consultor_filter)
        elif filtro_tipo == "coordenadores":
            base_queryset = base_queryset.filter(coordenador_filter)

        base_queryset = base_queryset.distinct()

        base_queryset = base_queryset.annotate(_order_name=Lower("username"))
        return base_queryset.order_by("_order_name", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_term"] = getattr(self, "search_term", "")

        valid_filters = {"associados", "nucleados", "consultores", "coordenadores"}
        current_filter = self.request.GET.get("tipo") or ""
        if current_filter not in valid_filters:
            current_filter = "todos"

        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")

        def build_url(filter_value: str | None) -> str:
            query_params = params.copy()
            if filter_value in valid_filters:
                query_params["tipo"] = filter_value
            else:
                query_params.pop("tipo", None)
            query_string = query_params.urlencode()
            return f"{self.request.path}?{query_string}" if query_string else self.request.path

        context["current_filter"] = current_filter
        context["associados_filter_url"] = build_url("associados")
        context["nucleados_filter_url"] = build_url("nucleados")
        context["consultores_filter_url"] = build_url("consultores")
        context["coordenadores_filter_url"] = build_url("coordenadores")
        context["todos_filter_url"] = build_url(None)
        context["is_associados_filter_active"] = current_filter == "associados"
        context["is_nucleados_filter_active"] = current_filter == "nucleados"
        context["is_consultores_filter_active"] = current_filter == "consultores"
        context["is_coordenadores_filter_active"] = current_filter == "coordenadores"

        organizacao = getattr(self, "organizacao", None)
        User = get_user_model()
        if organizacao:
            context["total_usuarios"] = User.objects.filter(organizacao=organizacao).count()
            context["total_associados"] = User.objects.filter(
                organizacao=organizacao, is_associado=True, nucleo__isnull=True
            ).count()
            context["total_nucleados"] = User.objects.filter(
                organizacao=organizacao, is_associado=True, nucleo__isnull=False
            ).count()
            consultor_filter = Q(user_type=UserType.CONSULTOR.value)
            context["total_consultores"] = (
                User.objects.filter(organizacao=organizacao).filter(consultor_filter).distinct().count()
            )
            coordenador_filter = (
                Q(user_type=UserType.COORDENADOR.value)
                | Q(is_coordenador=True)
                | Q(
                    participacoes__papel="coordenador",
                    participacoes__status="ativo",
                    participacoes__status_suspensao=False,
                )
            )
            context["total_coordenadores"] = (
                User.objects.filter(organizacao=organizacao).filter(coordenador_filter).distinct().count()
            )
        else:
            context["total_usuarios"] = 0
            context["total_associados"] = 0
            context["total_nucleados"] = 0
            context["total_consultores"] = 0
            context["total_coordenadores"] = 0

        context["has_search"] = bool(context["search_term"].strip())
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template="associados/_promover_grid.html",
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )
        return super().render_to_response(context, **response_kwargs)


class AssociadoPromoverFormView(NoSuperadminMixin, AssociadosRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "associados/promover_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organizacao = getattr(request.user, "organizacao", None)
        if self.organizacao is None:
            raise PermissionDenied(_("É necessário pertencer a uma organização para promover associados."))
        self.associado = get_object_or_404(
            User,
            pk=kwargs.get("pk"),
            organizacao=self.organizacao,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(self._build_form_context(**kwargs))

        return context

    def post(self, request, *args, **kwargs):
        raw_nucleado = request.POST.getlist("nucleado_nucleos")
        raw_consultor = request.POST.getlist("consultor_nucleos")
        raw_coordenador = request.POST.getlist("coordenador_nucleos")
        raw_remover_nucleado = request.POST.getlist("remover_nucleado_nucleos")
        raw_remover_consultor = request.POST.getlist("remover_consultor_nucleos")
        raw_remover_coordenador = request.POST.getlist("remover_coordenador_nucleos")

        def _parse_ids(values: list[str]) -> list[int]:
            parsed: list[int] = []
            seen: set[int] = set()
            for value in values:
                try:
                    pk = int(value)
                except (TypeError, ValueError):
                    continue
                if pk not in seen:
                    parsed.append(pk)
                    seen.add(pk)
            return parsed

        nucleado_ids = _parse_ids(raw_nucleado)
        consultor_ids = _parse_ids(raw_consultor)
        coordenador_ids = _parse_ids(raw_coordenador)
        remover_nucleado_ids = _parse_ids(raw_remover_nucleado)
        remover_consultor_ids = _parse_ids(raw_remover_consultor)
        remover_coordenador_ids = _parse_ids(raw_remover_coordenador)

        selected_coordenador_roles: dict[str, str] = {}
        coordenador_roles: dict[int, str] = {}
        for nucleo_id in coordenador_ids:
            role_value = (request.POST.get(f"coordenador_papel_{nucleo_id}") or "").strip()
            selected_coordenador_roles[str(nucleo_id)] = role_value
            if role_value:
                coordenador_roles[nucleo_id] = role_value

        all_selected_ids = set(nucleado_ids) | set(consultor_ids) | set(coordenador_ids)
        removal_ids = (
            set(remover_nucleado_ids)
            | set(remover_consultor_ids)
            | set(remover_coordenador_ids)
        )
        all_action_ids = all_selected_ids | removal_ids

        form_errors: list[str] = []

        if not all_action_ids:
            form_errors.append(
                _("Selecione ao menos um núcleo e papel para promoção ou remoção.")
            )

        valid_action_ids = set(
            Nucleo.objects.filter(organizacao=self.organizacao, id__in=all_action_ids).values_list("id", flat=True)
        )
        if len(valid_action_ids) != len(all_action_ids):
            form_errors.append(_("Selecione núcleos válidos da organização."))

        valid_ids = set(nid for nid in all_selected_ids if nid in valid_action_ids)

        papel_choices = {value for value, _ in ParticipacaoNucleo.PapelCoordenador.choices}
        for nucleo_id in coordenador_ids:
            papel = (request.POST.get(f"coordenador_papel_{nucleo_id}") or "").strip()
            if not papel:
                form_errors.append(_("Selecione um papel de coordenação para cada núcleo escolhido."))
                break
            if papel not in papel_choices:
                form_errors.append(_("Selecione um papel de coordenação válido."))
                break

        role_labels = dict(ParticipacaoNucleo.PapelCoordenador.choices)

        valid_coordenador_ids = {nid for nid in coordenador_roles.keys() if nid in valid_action_ids}

        if valid_coordenador_ids and not form_errors:
            ocupados = (
                ParticipacaoNucleo.objects.filter(
                    nucleo_id__in=valid_coordenador_ids,
                    papel="coordenador",
                    status="ativo",
                    papel_coordenador__in=set(coordenador_roles.values()),
                )
                .exclude(user=self.associado)
                .select_related("user", "nucleo")
            )
            for participacao in ocupados:
                papel = participacao.papel_coordenador
                if papel and coordenador_roles.get(participacao.nucleo_id) == papel:
                    form_errors.append(
                        _("O papel %(papel)s do núcleo %(nucleo)s já está ocupado por %(nome)s.")
                        % {
                            "papel": role_labels.get(papel, papel),
                            "nucleo": participacao.nucleo.nome,
                            "nome": participacao.user.display_name or participacao.user.username,
                        }
                    )

            restricted_roles = {
                ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
                ParticipacaoNucleo.PapelCoordenador.VICE_COORDENADOR,
            }
            selected_by_role: defaultdict[str, set[int]] = defaultdict(set)
            for nucleo_id, papel in coordenador_roles.items():
                if nucleo_id not in valid_coordenador_ids:
                    continue
                selected_by_role[papel].add(nucleo_id)

            existentes = defaultdict(set)
            if restricted_roles:
                existentes_qs = ParticipacaoNucleo.objects.filter(
                    user=self.associado,
                    papel="coordenador",
                    status="ativo",
                    papel_coordenador__in=restricted_roles,
                ).values_list("papel_coordenador", "nucleo_id")
                for papel, nucleo_id in existentes_qs:
                    existentes[papel].add(nucleo_id)

            for papel in restricted_roles:
                novos = selected_by_role.get(papel, set())
                if not novos:
                    continue
                atuais = existentes.get(papel, set())
                novos_diferentes = {nid for nid in novos if nid not in atuais}
                if atuais and novos_diferentes:
                    form_errors.append(
                        _("%(papel)s não pode ser atribuído a múltiplos núcleos diferentes.")
                        % {"papel": role_labels.get(papel, papel)}
                    )
                elif not atuais and len(novos_diferentes) > 1:
                    form_errors.append(
                        _("Selecione apenas um núcleo para o papel %(papel)s.")
                        % {"papel": role_labels.get(papel, papel)}
                    )

        conflict_nucleado = set(nucleado_ids) & set(remover_nucleado_ids)
        if conflict_nucleado:
            form_errors.append(
                _("Não é possível promover e remover a participação de nucleado no mesmo núcleo.")
            )

        conflict_consultor = set(consultor_ids) & set(remover_consultor_ids)
        if conflict_consultor:
            form_errors.append(
                _("Não é possível promover e remover a consultoria do mesmo núcleo.")
            )

        conflict_coordenador = set(coordenador_ids) & set(remover_coordenador_ids)
        if conflict_coordenador:
            form_errors.append(
                _("Não é possível promover e remover a coordenação no mesmo núcleo.")
            )

        overlapping_consultor_coordenador = set(consultor_ids) & set(coordenador_ids)
        if overlapping_consultor_coordenador:
            form_errors.append(_("Selecione apenas uma opção de promoção por núcleo."))

        valid_consultor_ids = {nid for nid in consultor_ids if nid in valid_action_ids}
        if valid_consultor_ids and not form_errors:
            consultores_ocupados = (
                Nucleo.objects.filter(id__in=valid_consultor_ids)
                .exclude(consultor__isnull=True)
                .exclude(consultor=self.associado)
                .select_related("consultor")
            )
            for nucleo in consultores_ocupados:
                form_errors.append(
                    _("O núcleo %(nucleo)s já possui o consultor %(nome)s.")
                    % {
                        "nucleo": nucleo.nome,
                        "nome": nucleo.consultor.display_name or nucleo.consultor.username,
                    }
                    )

        if remover_nucleado_ids and not form_errors:
            coordenador_ativos = set(
                ParticipacaoNucleo.objects.filter(
                    user=self.associado,
                    nucleo_id__in=remover_nucleado_ids,
                    status="ativo",
                    papel="coordenador",
                ).values_list("nucleo_id", flat=True)
            )
            bloqueados = coordenador_ativos - set(remover_coordenador_ids)
            if bloqueados:
                nomes = dict(
                    Nucleo.objects.filter(id__in=bloqueados).values_list("id", "nome")
                )
                for nucleo_id in bloqueados:
                    form_errors.append(
                        _("Remova a coordenação do núcleo %(nucleo)s antes de remover a participação.")
                        % {"nucleo": nomes.get(nucleo_id, nucleo_id)}
                    )

        if form_errors:
            context = self.get_context_data(
                selected_nucleado=[str(pk) for pk in nucleado_ids],
                selected_consultor=[str(pk) for pk in consultor_ids],
                selected_coordenador=[str(pk) for pk in coordenador_ids],
                selected_coordenador_roles=selected_coordenador_roles,
                selected_remover_nucleado=[str(pk) for pk in remover_nucleado_ids],
                selected_remover_consultor=[str(pk) for pk in remover_consultor_ids],
                selected_remover_coordenador=[str(pk) for pk in remover_coordenador_ids],
                form_errors=form_errors,
            )
            return self.render_to_response(context, status=400)

        if not valid_action_ids:
            context = self.get_context_data(
                selected_nucleado=[],
                selected_consultor=[],
                selected_coordenador=[],
                selected_coordenador_roles={},
                selected_remover_nucleado=[],
                selected_remover_consultor=[],
                selected_remover_coordenador=[],
                form_errors=[_("Nenhum núcleo válido foi selecionado.")],
            )
            return self.render_to_response(context, status=400)

        nucleos_queryset = {
            nucleo.id: nucleo
            for nucleo in Nucleo.objects.filter(organizacao=self.organizacao, id__in=valid_action_ids).select_for_update()
        }

        with transaction.atomic():
            participacoes_map = {
                participacao.nucleo_id: participacao
                for participacao in ParticipacaoNucleo.objects.select_for_update()
                .filter(user=self.associado, nucleo_id__in=valid_action_ids)
            }

            for nucleo_id in set(remover_consultor_ids) & valid_action_ids:
                nucleo = nucleos_queryset.get(nucleo_id)
                if nucleo and nucleo.consultor_id == self.associado.pk:
                    nucleo.consultor = None
                    nucleo.save(update_fields=["consultor"])

            if valid_consultor_ids:
                for nucleo_id in valid_consultor_ids:
                    nucleo = nucleos_queryset.get(nucleo_id)
                    if not nucleo:
                        continue
                    if nucleo.consultor_id != self.associado.pk:
                        nucleo.consultor = self.associado
                        nucleo.save(update_fields=["consultor"])

            for nucleo_id in valid_ids:
                nucleo = nucleos_queryset.get(nucleo_id)
                if not nucleo:
                    continue
                assign_coordenador = nucleo_id in coordenador_roles
                assign_nucleado = nucleo_id in nucleado_ids
                if not assign_coordenador and not assign_nucleado:
                    continue
                participacao = participacoes_map.get(nucleo_id)
                if not participacao:
                    participacao = ParticipacaoNucleo.objects.create(
                        nucleo=nucleo,
                        user=self.associado,
                        status="ativo",
                    )
                    participacoes_map[nucleo_id] = participacao

                update_fields: set[str] = set()
                if participacao.status != "ativo":
                    participacao.status = "ativo"
                    update_fields.add("status")
                if participacao.status_suspensao:
                    participacao.status_suspensao = False
                    update_fields.add("status_suspensao")
                if assign_coordenador:
                    if participacao.papel != "coordenador":
                        participacao.papel = "coordenador"
                        update_fields.add("papel")
                    novo_papel = coordenador_roles.get(nucleo_id)
                    if participacao.papel_coordenador != novo_papel:
                        participacao.papel_coordenador = novo_papel
                        update_fields.add("papel_coordenador")
                elif assign_nucleado and participacao.papel != "coordenador":
                    if participacao.papel != "membro":
                        participacao.papel = "membro"
                        update_fields.add("papel")
                    if participacao.papel_coordenador:
                        participacao.papel_coordenador = None
                        update_fields.add("papel_coordenador")
                if update_fields:
                    participacao.save(update_fields=list(update_fields))

            for nucleo_id in set(remover_coordenador_ids) & valid_action_ids:
                participacao = participacoes_map.get(nucleo_id)
                if not participacao or participacao.papel != "coordenador":
                    continue
                update_fields: set[str] = set()
                if participacao.papel != "membro":
                    participacao.papel = "membro"
                    update_fields.add("papel")
                if participacao.papel_coordenador:
                    participacao.papel_coordenador = None
                    update_fields.add("papel_coordenador")
                if participacao.status != "ativo":
                    participacao.status = "ativo"
                    update_fields.add("status")
                if participacao.status_suspensao:
                    participacao.status_suspensao = False
                    update_fields.add("status_suspensao")
                if update_fields:
                    participacao.save(update_fields=list(update_fields))

            for nucleo_id in set(remover_nucleado_ids) & valid_action_ids:
                participacao = participacoes_map.get(nucleo_id)
                if not participacao:
                    continue
                update_fields: set[str] = set()
                if participacao.status != "inativo":
                    participacao.status = "inativo"
                    update_fields.add("status")
                if participacao.papel != "membro":
                    participacao.papel = "membro"
                    update_fields.add("papel")
                if participacao.papel_coordenador:
                    participacao.papel_coordenador = None
                    update_fields.add("papel_coordenador")
                if participacao.status_suspensao:
                    participacao.status_suspensao = False
                    update_fields.add("status_suspensao")
                if update_fields:
                    participacao.save(update_fields=list(update_fields))

        remaining_participacoes = ParticipacaoNucleo.objects.filter(
            user=self.associado,
            status="ativo",
            status_suspensao=False,
        )
        has_coordenador = remaining_participacoes.filter(papel="coordenador").exists()
        has_participacao = remaining_participacoes.exists()
        has_consultor = Nucleo.objects.filter(
            organizacao=self.organizacao,
            consultor=self.associado,
        ).exists()

        updates: list[str] = []
        if self.associado.is_coordenador != has_coordenador:
            self.associado.is_coordenador = has_coordenador
            updates.append("is_coordenador")

        allowed_types = {
            UserType.ASSOCIADO,
            UserType.NUCLEADO,
            UserType.CONSULTOR,
            UserType.COORDENADOR,
        }
        if self.associado.user_type in allowed_types:
            if has_coordenador:
                target_type = UserType.COORDENADOR
            elif has_consultor:
                target_type = UserType.CONSULTOR
            elif has_participacao:
                target_type = UserType.NUCLEADO
            else:
                target_type = UserType.ASSOCIADO
            if self.associado.user_type != target_type:
                self.associado.user_type = target_type
                updates.append("user_type")

        if updates:
            self.associado.save(update_fields=updates)

        context = self.get_context_data(
            selected_nucleado=[],
            selected_consultor=[],
            selected_coordenador=[],
            selected_coordenador_roles={},
            selected_remover_nucleado=[],
            selected_remover_consultor=[],
            selected_remover_coordenador=[],
            success_message=_("Promoção registrada com sucesso."),
            form_errors=[],
        )
        return self.render_to_response(context)

    def _build_form_context(self, **kwargs):
        selected_nucleado = [str(value) for value in kwargs.get("selected_nucleado") or []]
        selected_consultor = [str(value) for value in kwargs.get("selected_consultor") or []]
        selected_coordenador = [str(value) for value in kwargs.get("selected_coordenador") or []]
        selected_remover_nucleado = [
            str(value) for value in kwargs.get("selected_remover_nucleado") or []
        ]
        selected_remover_consultor = [
            str(value) for value in kwargs.get("selected_remover_consultor") or []
        ]
        selected_remover_coordenador = [
            str(value) for value in kwargs.get("selected_remover_coordenador") or []
        ]
        raw_roles = kwargs.get("selected_coordenador_roles") or {}
        selected_coordenador_roles = {str(key): value for key, value in raw_roles.items()}
        form_errors = kwargs.get("form_errors") or []
        success_message = kwargs.get("success_message")

        nucleos_qs = (
            Nucleo.objects.filter(organizacao=self.organizacao)
            .select_related("consultor")
            .prefetch_related(
                Prefetch(
                    "participacoes",
                    queryset=ParticipacaoNucleo.objects.filter(status="ativo", papel="coordenador").select_related(
                        "user"
                    ),
                )
            )
            .order_by("nome")
        )

        role_labels = dict(ParticipacaoNucleo.PapelCoordenador.choices)
        participacoes_usuario = list(
            ParticipacaoNucleo.objects.filter(
                user=self.associado,
                status="ativo",
                status_suspensao=False,
            ).values("nucleo_id", "papel", "papel_coordenador")
        )

        current_memberships: set[str] = set()
        user_roles_by_nucleo: defaultdict[str, list[str]] = defaultdict(list)
        user_role_map: defaultdict[str, list[str]] = defaultdict(list)
        for participacao in participacoes_usuario:
            nucleo_id = str(participacao["nucleo_id"])
            current_memberships.add(nucleo_id)
            if participacao["papel"] == "coordenador" and participacao["papel_coordenador"]:
                papel = participacao["papel_coordenador"]
                user_roles_by_nucleo[nucleo_id].append(papel)
                user_role_map[papel].append(nucleo_id)

        nucleos: list[dict[str, object]] = []
        for nucleo in nucleos_qs:
            participacoes = list(nucleo.participacoes.all())
            unavailable_roles: set[str] = set()
            coordenadores: list[dict[str, object]] = []
            unavailable_messages: dict[str, str] = {}

            for participacao in participacoes:
                papel = participacao.papel_coordenador
                if not papel:
                    continue
                unavailable_roles.add(papel)
                is_target = participacao.user_id == self.associado.pk
                coordenadores.append(
                    {
                        "papel": papel,
                        "user_name": participacao.user.display_name or participacao.user.username,
                        "user_id": participacao.user_id,
                        "is_target_user": is_target,
                    }
                )
                if not is_target:
                    unavailable_messages[papel] = _("%(papel)s ocupado por %(nome)s.") % {
                        "papel": role_labels.get(papel, papel),
                        "nome": participacao.user.display_name or participacao.user.username,
                    }

            coordenadores.sort(key=lambda item: role_labels.get(item["papel"], item["papel"]))

            nucleos.append(
                {
                    "id": str(nucleo.pk),
                    "nome": nucleo.nome,
                    "avatar_url": nucleo.avatar.url if nucleo.avatar else "",
                    "consultor_name": (
                        nucleo.consultor.display_name or nucleo.consultor.username if nucleo.consultor else ""
                    ),
                    "is_current_consultor": nucleo.consultor_id == self.associado.pk,
                    "is_current_member": str(nucleo.pk) in current_memberships,
                    "is_current_coordinator": bool(
                        user_roles_by_nucleo.get(str(nucleo.pk), [])
                    ),
                    "coordenadores": coordenadores,
                    "unavailable_roles": sorted(unavailable_roles),
                    "user_current_roles": user_roles_by_nucleo.get(str(nucleo.pk), []),
                    "unavailable_messages_json": json.dumps(unavailable_messages),
                }
            )

        restricted_roles = [
            ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
            ParticipacaoNucleo.PapelCoordenador.VICE_COORDENADOR,
        ]

        return {
            "associado": self.associado,
            "nucleos": nucleos,
            "coordenador_role_choices": ParticipacaoNucleo.PapelCoordenador.choices,
            "coordenador_role_labels": role_labels,
            "restricted_roles": [role for role in restricted_roles if role],
            "selected_nucleado": selected_nucleado,
            "selected_consultor": selected_consultor,
            "selected_coordenador": selected_coordenador,
            "selected_coordenador_roles": selected_coordenador_roles,
            "selected_remover_nucleado": selected_remover_nucleado,
            "selected_remover_consultor": selected_remover_consultor,
            "selected_remover_coordenador": selected_remover_coordenador,
            "form_errors": form_errors,
            "success_message": success_message,
            "user_role_map_json": json.dumps(dict(user_role_map)),
        }


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        organizacao = getattr(self.request.user, "organizacao", None)
        if not organizacao:
            return User.objects.none()
        return User.objects.filter(organizacao=organizacao, is_associado=True)

    def get_permission_classes(self):
        """Retorna lista de classes de permissão baseadas na ação atual."""
        permission_classes = [IsAuthenticated]
        if self.action in ["create", "update", "partial_update"]:
            if self.request.user.get_tipo_usuario == "admin":
                permission_classes.append(IsAdmin)
            elif self.request.user.get_tipo_usuario == "coordenador":
                permission_classes.append(IsCoordenador)
        return permission_classes

    def get_permissions(self):
        return [permission() for permission in self.get_permission_classes()]

    def perform_create(self, serializer):
        organizacao = self.request.user.organizacao
        if self.request.user.get_tipo_usuario == "admin":
            serializer.save(organizacao=organizacao)
        elif self.request.user.get_tipo_usuario == "coordenador":
            serializer.save(organizacao=organizacao, is_associado=False, is_staff=False)
        else:
            raise PermissionError("Você não tem permissão para criar usuários.")
