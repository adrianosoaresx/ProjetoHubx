import os
import uuid
from pathlib import Path

from django.conf import settings
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
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import (
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
from django.views.generic import FormView, ListView
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
from nucleos.models import ConviteNucleo
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


# ====================== PERFIL ======================


@login_required
def perfil(request):
    """Exibe a página de perfil privado do usuário."""
    user = request.user

    portfolio_recent = _portfolio_for(user, request.user, limit=6)
    hero_title, hero_subtitle = _profile_hero_names(user)

    context = {
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "profile": user,
        "is_owner": True,
        "portfolio_recent": portfolio_recent,
        "portfolio_form": MediaForm(),
        "portfolio_show_form": False,
        "portfolio_q": "",
    }

    default_section, default_url = _perfil_default_section_url(request, allow_owner_sections=True)
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

    if section == "portfolio":
        q = request.GET.get("q", "").strip()
        medias_qs = Midia.objects.visible_to(viewer, profile).select_related("user").prefetch_related("tags").order_by(
            "-created_at"
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
        if is_owner:
            bio = getattr(profile, "biografia", "") or getattr(profile, "bio", "")
            context.update(
                {
                    "user": profile,
                    "bio": bio,
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
    if request.method in {"GET", "HEAD"} and not _is_htmx_or_ajax(request):
        extra_params = {"info_view": "edit"} if request.method == "GET" else None
        return _redirect_to_profile_section(request, "info", extra_params)

    if request.method == "POST":
        form = InformacoesPessoaisForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if getattr(form, "email_changed", False):
                messages.info(request, _("Confirme o novo e-mail enviado."))
            else:
                messages.success(request, _("Informações do perfil atualizadas."))
            return _redirect_to_profile_section(request, "info")
    else:
        form = InformacoesPessoaisForm(instance=request.user)

    return render(
        request,
        "perfil/partials/info_form.html",
        {
            "form": form,
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

    if request.method == "GET":
        return render(request, "accounts/delete_account_confirm.html")

    if request.method != "POST":
        return redirect("accounts:excluir_conta")

    if request.POST.get("confirm") != "EXCLUIR":
        messages.error(request, _("Confirme digitando EXCLUIR."))
        return redirect("accounts:excluir_conta")

    with transaction.atomic():
        user = request.user
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
    logout(request)
    messages.success(
        request,
        _("Sua conta foi excluída com sucesso. Você pode reativá-la em até 30 dias."),
    )
    return redirect("core:home")


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
            tipo_mapping = {
                TokenAcesso.TipoUsuario.ASSOCIADO: UserType.ASSOCIADO,
                TokenAcesso.TipoUsuario.CONVIDADO: UserType.CONVIDADO,
            }
            mapped_user_type = tipo_mapping.get(token_obj.tipo_destino)
            if not mapped_user_type:
                messages.error(request, _("Convite inválido."))
                return redirect("tokens:token")
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

            convite_nucleo = (
                ConviteNucleo.objects.select_related("nucleo")
                .filter(token_obj=token_obj)
                .first()
            )
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
            _(
                "Usuário %(username)s (%(tipo)s) adicionado com sucesso."
            )
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
                | Q(user_type__in=[UserType.NUCLEADO.value, UserType.COORDENADOR.value])
                | Q(is_coordenador=True)
            )
            .select_related("organizacao", "nucleo")
        )
        # TODO: unify "user_type" and "is_associado" fields to avoid duplicate state
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(contato__icontains=q))

        filtro_tipo = self.request.GET.get("tipo")
        if filtro_tipo == "associados":
            qs = qs.filter(is_associado=True, nucleo__isnull=True)
        elif filtro_tipo == "nucleados":
            qs = qs.filter(is_associado=True, nucleo__isnull=False)

        # Ordenação alfabética por username (case-insensitive)
        qs = qs.annotate(_user=Lower("username"))
        return qs.order_by("_user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_filter = self.request.GET.get("tipo") or ""
        if current_filter not in {"associados", "nucleados"}:
            current_filter = "todos"

        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")

        def build_url(filter_value: str | None) -> str:
            query_params = params.copy()
            if filter_value in {"associados", "nucleados"}:
                query_params["tipo"] = filter_value
            else:
                query_params.pop("tipo", None)
            query_string = query_params.urlencode()
            return f"{self.request.path}?{query_string}" if query_string else self.request.path

        context["current_filter"] = current_filter
        context["associados_filter_url"] = build_url("associados")
        context["nucleados_filter_url"] = build_url("nucleados")
        context["todos_filter_url"] = build_url(None)
        context["is_associados_filter_active"] = current_filter == "associados"
        context["is_nucleados_filter_active"] = current_filter == "nucleados"

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
        else:
            context["total_usuarios"] = 0
            context["total_associados"] = 0
            context["total_nucleados"] = 0
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
                    ]
                )
                | Q(is_associado=True)
                | Q(is_coordenador=True)
            )
            .select_related("organizacao", "nucleo")
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

        base_queryset = base_queryset.annotate(_order_name=Lower("username"))
        return base_queryset.order_by("_order_name", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_term"] = getattr(self, "search_term", "")
        context.setdefault("total_usuarios", None)
        context.setdefault("total_associados", None)
        context.setdefault("total_nucleados", None)
        context["has_search"] = bool(context["search_term"].strip())
        return context


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
