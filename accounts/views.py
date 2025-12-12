import json
import logging
import os
import uuid
from pathlib import Path

from django.conf import settings

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile, File
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, BooleanField, Count, Exists, OuterRef, Q, Value
from django.db.models.functions import Lower
from django.core.cache import cache
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlencode
from django_ratelimit.decorators import ratelimit
from rest_framework import viewsets

from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)

from accounts.serializers import UserSerializer
from accounts.tasks import (
    send_cancel_delete_email,
    send_confirmation_email,
    send_password_reset_email,
)
from audit.services import hash_ip, log_audit
from core.permissions import (
    IsAdmin,
    IsCoordenador,
)
from nucleos.models import ConviteNucleo
from eventos.models import Evento, PreRegistroConvite
from tokens.models import TOTPDevice, TokenAcesso
from tokens.services import find_token_by_code
from tokens.utils import get_client_ip
from organizacoes.utils import validate_cnpj
from feed.models import Bookmark, Flag, Post, Reacao
from .forms import (
    CPF_REUSE_ERROR,
    IDENTIFIER_REQUIRED_ERROR,
    EmailLoginForm,
    InformacoesPessoaisForm,
    TotpLoginForm,
    UserRatingForm,
)
from .utils import build_profile_section_url, is_htmx_or_ajax, redirect_to_profile_section
from .models import AccountToken, LoginAttempt, SecurityEvent, UserRating, UserType
from .validators import cpf_validator

User = get_user_model()

PERFIL_DEFAULT_SECTION = "info"
PERFIL_SECTION_URLS = {
    "info": "accounts:perfil_info_partial",
}

PERFIL_OWNER_SECTION_URLS = {
    **PERFIL_SECTION_URLS,
    "conexoes": "conexoes:perfil_conexoes_partial",
}

RATINGS_PER_PAGE = 6


def _get_rating_stats(rating_qs):
    stats = rating_qs.aggregate(media=Avg("score"), total=Count("id"))
    media = stats["media"]
    display = f"{media:.1f}".replace(".", ",") if media is not None else ""
    return stats, media, display


def _get_rating_page(rating_qs, *, page_number=1):
    paginator = Paginator(rating_qs.order_by("-created_at"), RATINGS_PER_PAGE)
    return paginator.get_page(page_number)


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
        if section == "info" and params.get("info_view") == "edit":
            url_name = "accounts:perfil_sections_info"
            params.pop("info_view", None)
        elif section == "conexoes":
            view_mode = (params.get("view") or "").strip().lower()
            if view_mode == "buscar":
                url_name = "conexoes:perfil_conexoes_buscar"

    url = reverse(url_name, args=url_args)
    query_string = params.urlencode()
    if query_string:
        url = f"{url}?{query_string}"

    return section, url


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


def _can_promote_profile(viewer, profile) -> bool:
    if viewer is None or not getattr(viewer, "is_authenticated", False):
        return False

    viewer_type = getattr(viewer, "get_tipo_usuario", None)
    if viewer_type not in {UserType.ADMIN.value, UserType.OPERADOR.value}:
        return False

    profile_type_attr = getattr(profile, "get_tipo_usuario", None)
    profile_type = profile_type_attr() if callable(profile_type_attr) else profile_type_attr
    if profile_type in {UserType.ADMIN.value, UserType.OPERADOR.value}:
        return False

    viewer_org = getattr(viewer, "organizacao_id", None)
    profile_org = getattr(profile, "organizacao_id", None)
    return viewer_org is not None and profile_org is not None and viewer_org == profile_org


def _can_toggle_user_active(viewer, profile) -> bool:
    if not _can_manage_profile(viewer, profile):
        return False

    viewer_type = getattr(viewer, "get_tipo_usuario", None)
    return viewer_type in {
        UserType.ROOT.value,
        UserType.ADMIN.value,
        UserType.OPERADOR.value,
    }


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


def _build_profile_info_context(request, profile, *, is_owner: bool, viewer: User | None):
    context: dict[str, object] = {
        "profile": profile,
        "is_owner": is_owner,
    }

    can_manage = _can_manage_profile(viewer, profile) if viewer else False
    context["can_manage"] = can_manage

    if can_manage:
        bio = getattr(profile, "biografia", "") or getattr(profile, "bio", "")
        identifiers = {
            "public_id": str(profile.public_id),
            "username": profile.username,
        }
        context.update(
            {
                "user": profile,
                "bio": bio,
                "manage_target_public_id": profile.public_id,
                "manage_target_username": profile.username,
                "manage_target_query": urlencode(identifiers),
                "can_toggle_active": _can_toggle_user_active(viewer, profile),
                "activate_user_url": reverse("accounts:activate_user"),
                "deactivate_user_url": reverse("accounts:deactivate_user"),
            }
        )

    return context


def _render_profile_info_partial(request, profile, *, is_owner: bool, viewer: User | None):
    context = _build_profile_info_context(request, profile, is_owner=is_owner, viewer=viewer)
    return render(request, "perfil/partials/detail_informacoes.html", context)


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

    hero_title, hero_subtitle = _profile_hero_names(target_user)

    allow_owner_sections = _can_manage_profile(viewer, target_user)

    portfolio_medias = list(
        target_user.medias.visible_to(viewer, target_user)
        .select_related("user")
        .order_by("-created_at")
    )

    profile_posts = (
        Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
        .prefetch_related("reacoes", "comments")
        .filter(deleted=False, autor=target_user)
        .annotate(
            like_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="like", reacoes__deleted=False),
                distinct=True,
            ),
            share_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="share", reacoes__deleted=False),
                distinct=True,
            ),
        )
    )

    if viewer.is_authenticated:
        profile_posts = profile_posts.annotate(
            is_bookmarked=Exists(
                Bookmark.objects.filter(post=OuterRef("pk"), user=viewer, deleted=False)
            ),
            is_flagged=Exists(
                Flag.objects.filter(post=OuterRef("pk"), user=viewer, deleted=False)
            ),
            is_liked=Exists(
                Reacao.objects.filter(
                    post=OuterRef("pk"),
                    user=viewer,
                    vote="like",
                    deleted=False,
                )
            ),
            is_shared=Exists(
                Reacao.objects.filter(
                    post=OuterRef("pk"),
                    user=viewer,
                    vote="share",
                    deleted=False,
                )
            ),
        )
    else:
        profile_posts = profile_posts.annotate(
            is_bookmarked=Value(False, output_field=BooleanField()),
            is_flagged=Value(False, output_field=BooleanField()),
            is_liked=Value(False, output_field=BooleanField()),
            is_shared=Value(False, output_field=BooleanField()),
        )

    profile_posts = profile_posts.order_by("-created_at").distinct()

    rating_qs = UserRating.objects.filter(rated_user=target_user).select_related(
        "rated_by"
    )
    avaliacao_stats, avaliacao_media, avaliacao_display = _get_rating_stats(rating_qs)
    ratings_page = _get_rating_page(rating_qs)
    user_rating = rating_qs.filter(rated_by=request.user).first()

    can_promote_profile = _can_promote_profile(viewer, target_user)
    promote_profile_url = None
    if can_promote_profile:
        promote_profile_url = reverse(
            "membros:membro_promover_form", args=[target_user.pk]
        )

    context = {
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "profile": target_user,
        "is_owner": is_owner,
        "portfolio_medias": portfolio_medias,
        "profile_posts": profile_posts,
        "can_promote_profile": can_promote_profile,
        "promote_profile_url": promote_profile_url,
        "perfil_avaliacao_media": avaliacao_media,
        "perfil_avaliacao_display": avaliacao_display,
        "perfil_avaliacao_total": avaliacao_stats["total"],
        "perfil_avaliacoes_page": ratings_page,
        "perfil_avaliacoes_fetch_url": reverse(
            "accounts:perfil_avaliacoes_carousel", args=[target_user.public_id]
        ),
        "perfil_avaliacoes_empty_message": _(
            "Nenhuma avaliação disponível até o momento."
        ),
        "perfil_feedback_exists": user_rating is not None,
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
    hero_title, hero_subtitle = _profile_hero_names(perfil)

    viewer = request.user if request.user.is_authenticated else None
    portfolio_medias = list(
        perfil.medias.visible_to(viewer, perfil).select_related("user").order_by("-created_at")
    )

    profile_posts = (
        Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
        .prefetch_related("reacoes", "comments")
        .filter(deleted=False, autor=perfil, tipo_feed="global")
        .annotate(
            like_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="like", reacoes__deleted=False),
                distinct=True,
            ),
            share_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="share", reacoes__deleted=False),
                distinct=True,
            ),
        )
    )

    if request.user.is_authenticated:
        profile_posts = profile_posts.annotate(
            is_bookmarked=Exists(
                Bookmark.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)
            ),
            is_flagged=Exists(
                Flag.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)
            ),
            is_liked=Exists(
                Reacao.objects.filter(
                    post=OuterRef("pk"),
                    user=request.user,
                    vote="like",
                    deleted=False,
                )
            ),
            is_shared=Exists(
                Reacao.objects.filter(
                    post=OuterRef("pk"),
                    user=request.user,
                    vote="share",
                    deleted=False,
                )
            ),
        )
    else:
        profile_posts = profile_posts.annotate(
            is_bookmarked=Value(False, output_field=BooleanField()),
            is_flagged=Value(False, output_field=BooleanField()),
            is_liked=Value(False, output_field=BooleanField()),
            is_shared=Value(False, output_field=BooleanField()),
        )

    profile_posts = profile_posts.order_by("-created_at").distinct()

    rating_qs = UserRating.objects.filter(rated_user=perfil).select_related("rated_by")
    avaliacao_stats, avaliacao_media, avaliacao_display = _get_rating_stats(rating_qs)
    ratings_page = _get_rating_page(rating_qs)
    user_rating = None
    if request.user.is_authenticated:
        user_rating = rating_qs.filter(rated_by=request.user).first()

    can_promote_profile = _can_promote_profile(viewer, perfil)
    promote_profile_url = None
    if can_promote_profile:
        promote_profile_url = reverse("membros:membro_promover_form", args=[perfil.pk])

    context = {
        "perfil": perfil,
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "is_owner": request.user == perfil,
        "portfolio_medias": portfolio_medias,
        "profile_posts": profile_posts,
        "can_promote_profile": can_promote_profile,
        "promote_profile_url": promote_profile_url,
        "perfil_avaliacao_media": avaliacao_media,
        "perfil_avaliacao_display": avaliacao_display,
        "perfil_avaliacao_total": avaliacao_stats["total"],
        "perfil_avaliar_url": reverse("accounts:perfil_avaliar", args=[perfil.public_id]),
        "perfil_avaliar_identifier": str(perfil.public_id),
        "perfil_feedback_exists": user_rating is not None,
        "perfil_avaliacoes_page": ratings_page,
        "perfil_avaliacoes_fetch_url": reverse(
            "accounts:perfil_avaliacoes_carousel", args=[perfil.public_id]
        ),
        "perfil_avaliacoes_empty_message": _(
            "Nenhuma avaliação disponível até o momento."
        ),
    }

    default_section, default_url = _perfil_default_section_url(request)
    context.update(
        {
            "perfil_default_section": default_section,
            "perfil_default_url": default_url,
        }
    )

    return render(request, "perfil/publico.html", context)


@login_required
def perfil_avaliar(request, public_id):
    perfil = get_object_or_404(User, public_id=public_id, perfil_publico=True)
    redirect_url = reverse("accounts:perfil_publico_uuid", args=[perfil.public_id])

    def _rating_error_response(message, *, status=403):
        if request.headers.get("HX-Request"):
            response = HttpResponse(status=status)
            response["HX-Trigger"] = json.dumps({
                "user-rating:error": {"message": str(message)}
            })
            return response

        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"detail": message}, status=status)

        messages.error(request, message)
        return redirect(redirect_url)

    viewer_org = getattr(request.user, "organizacao_id", None)
    profile_org = getattr(perfil, "organizacao_id", None)
    if not viewer_org or not profile_org or viewer_org != profile_org:
        return _rating_error_response(
            _("Você só pode avaliar perfis da sua organização."),
        )
    if request.user == perfil:
        return _rating_error_response(_("Você não pode avaliar seu próprio perfil."))
    existing_rating = UserRating.objects.filter(
        rated_user=perfil, rated_by=request.user
    ).first()

    def _rating_payload():
        stats = UserRating.objects.filter(rated_user=perfil).aggregate(
            media=Avg("score"),
            total=Count("id"),
        )
        media = stats["media"]
        display = f"{media:.1f}".replace(".", ",") if media is not None else ""
        return {"average": media, "display": display, "total": stats["total"]}

    if request.method in {"GET", "HEAD"}:
        context = {
            "perfil": perfil,
            "feedback": existing_rating,
            "form": UserRatingForm(user=request.user, rated_user=perfil),
            "feedback_exists": existing_rating is not None,
        }
        return render(request, "perfil/partials/perfil_feedback_modal.html", context)

    if existing_rating:
        error_message = _("Você já avaliou este perfil.")
        if request.headers.get("HX-Request"):
            response = HttpResponse(status=409)
            response["HX-Trigger"] = json.dumps({
                "user-rating:error": {"message": error_message}
            })
            return response
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"detail": error_message}, status=409)
        messages.info(request, error_message)
        return redirect(redirect_url)

    if request.method != "POST":
        return HttpResponseBadRequest()

    form = UserRatingForm(request.POST, user=request.user, rated_user=perfil)
    if form.is_valid():
        form.save()
        payload = _rating_payload()

        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps({
                "user-rating:submitted": payload
            })
            return response

        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse(payload, status=201)

        messages.success(request, _("Avaliação registrada com sucesso."))
        return redirect(redirect_url)

    context = {
        "perfil": perfil,
        "form": form,
        "feedback_exists": False,
    }
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({"errors": form.errors}, status=400)
    return render(
        request,
        "perfil/partials/perfil_feedback_modal.html",
        context,
        status=400,
    )


@require_GET
def perfil_avaliacoes_carousel(request, public_id):
    perfil = get_object_or_404(User, public_id=public_id)
    viewer = request.user if request.user.is_authenticated else None
    can_view = viewer and (_can_manage_profile(viewer, perfil) or viewer == perfil)
    if not perfil.perfil_publico and not can_view:
        return HttpResponseForbidden()
    rating_qs = UserRating.objects.filter(rated_user=perfil).select_related("rated_by")
    page_number = request.GET.get("page") or 1
    ratings_page = _get_rating_page(rating_qs, page_number=page_number)

    html = render_to_string(
        "perfil/partials/avaliacoes_carousel_slide.html",
        {
            "avaliacoes": list(ratings_page.object_list),
            "page_number": ratings_page.number,
            "empty_message": _("Nenhuma avaliação disponível até o momento."),
        },
        request=request,
    )

    return JsonResponse(
        {
            "html": html,
            "page": ratings_page.number,
            "total_pages": ratings_page.paginator.num_pages,
            "count": ratings_page.paginator.count,
        }
    )


@require_GET
def perfil_section(request, section):
    profile, is_owner, error = _resolve_profile_for_partial(request)
    if error:
        return error

    viewer = request.user if request.user.is_authenticated else None
    context = _build_profile_info_context(
        request,
        profile,
        is_owner=is_owner,
        viewer=viewer,
    )

    if section == "info":
        if context.get("can_manage"):
            template = "perfil/partials/detail_informacoes.html"
        else:
            template = "perfil/partials/publico_informacoes.html"

    else:
        return HttpResponseBadRequest("Invalid section")

    return render(request, template, context)


def _profile_toggle_response(request, target_user, *, is_owner: bool):
    if request.headers.get("HX-Request"):
        return _render_profile_info_partial(
            request,
            target_user,
            is_owner=is_owner,
            viewer=request.user,
        )

    extra_params: dict[str, str | None] = {"info_view": None}
    if not is_owner:
        extra_params.update(
            {
                "public_id": str(target_user.public_id),
                "username": target_user.username,
            }
        )

    return redirect_to_profile_section(request, "info", extra_params)


@login_required
@require_POST
def deactivate_user(request):
    target_user = _resolve_management_target_user(request)

    if not _can_toggle_user_active(request.user, target_user):
        raise PermissionDenied

    if not target_user.is_active:
        return HttpResponseBadRequest(_("Usuário já está inativo."))

    target_user.is_active = False
    target_user.save(update_fields=["is_active"])

    ip = get_client_ip(request)
    SecurityEvent.objects.create(
        usuario=target_user,
        evento="usuario_desativado",
        ip=ip,
    )
    log_audit(
        request.user,
        "user_deactivated",
        object_type="User",
        object_id=str(target_user.id),
        ip_hash=hash_ip(ip),
        metadata={"target_username": target_user.username},
    )

    return _profile_toggle_response(request, target_user, is_owner=target_user == request.user)


@login_required
@require_POST
def activate_user(request):
    target_user = _resolve_management_target_user(request)

    if not _can_toggle_user_active(request.user, target_user):
        raise PermissionDenied

    if target_user.is_active:
        return HttpResponseBadRequest(_("Usuário já está ativo."))

    target_user.is_active = True
    target_user.save(update_fields=["is_active"])

    ip = get_client_ip(request)
    SecurityEvent.objects.create(
        usuario=target_user,
        evento="usuario_ativado",
        ip=ip,
    )
    log_audit(
        request.user,
        "user_activated",
        object_type="User",
        object_id=str(target_user.id),
        ip_hash=hash_ip(ip),
        metadata={"target_username": target_user.username},
    )

    return _profile_toggle_response(request, target_user, is_owner=target_user == request.user)


@login_required
def perfil_info(request):
    target_user = _resolve_management_target_user(request)
    is_self = target_user == request.user

    if request.method in {"GET", "HEAD"} and not is_htmx_or_ajax(request):
        extra_params: dict[str, str | None] | None = {"info_view": "edit"}
        if not is_self:
            extra_params.update(
                {
                    "public_id": str(target_user.public_id),
                    "username": target_user.username,
                }
            )
        return redirect_to_profile_section(request, "info", extra_params)

    target_identifiers: dict[str, str] = {}
    if not is_self:
        target_identifiers = {
            "public_id": str(target_user.public_id),
            "username": target_user.username,
        }

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
            if target_identifiers:
                extra_params.update(target_identifiers)
            return redirect_to_profile_section(request, "info", extra_params)
        if not is_htmx_or_ajax(request):
            extra_params = {"info_view": "edit"}
            if target_identifiers:
                extra_params.update(target_identifiers)
            return redirect_to_profile_section(request, "info", extra_params)
    else:
        form = InformacoesPessoaisForm(instance=target_user)

    cancel_params: dict[str, str | None] = {"info_view": None}
    if target_identifiers:
        cancel_params.update(target_identifiers)

    cancel_fallback_url = build_profile_section_url(
        request,
        "info",
        cancel_params,
    )
    cancel_hx_get_url = reverse("accounts:perfil_info_partial")
    if target_identifiers:
        cancel_hx_get_url = f"{cancel_hx_get_url}?{urlencode(target_identifiers)}"

    return render(
        request,
        "perfil/partials/info_form.html",
        {
            "form": form,
            "target_user": target_user,
            "is_self": is_self,
            "back_href": cancel_fallback_url,
            "cancel_fallback_url": cancel_fallback_url,
            "cancel_component_config": {
                "href": cancel_fallback_url,
                "fallback_href": cancel_fallback_url,
                "aria_label": _("Cancelar edição"),
                "hx_get": cancel_hx_get_url,
                "hx_target": "closest section",
                "hx_swap": "innerHTML",
                "hx_push_url": cancel_fallback_url,
            },
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


def _user_requires_totp(user: User) -> bool:
    return (
        getattr(user, "two_factor_enabled", False)
        and getattr(user, "two_factor_secret", None)
        and TOTPDevice.objects.filter(usuario=user).exists()
    )


def _clear_pending_2fa(request):
    request.session.pop("pending_2fa_user_id", None)
    request.session.modified = True


def _get_pending_2fa_user(request):
    user_id = request.session.get("pending_2fa_user_id")
    if not user_id:
        return None
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        _clear_pending_2fa(request)
        return None
    if not user.is_active:
        _clear_pending_2fa(request)
        return None
    lock_until = cache.get(f"lockout_user_{user.pk}")
    if lock_until and lock_until > timezone.now():
        _clear_pending_2fa(request)
        return None
    if not _user_requires_totp(user):
        _clear_pending_2fa(request)
        return None
    return user


def _register_login_success(user: User, request):
    login(request, user, backend="accounts.backends.EmailBackend")
    cache.delete(f"failed_login_attempts_user_{user.pk}")
    cache.delete(f"lockout_user_{user.pk}")
    LoginAttempt.objects.create(
        usuario=user,
        email=user.email,
        sucesso=True,
        ip=get_client_ip(request),
    )


# ====================== AUTENTICAÇÃO ======================


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:perfil")

    form = EmailLoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        if form.requires_totp:
            request.session["pending_2fa_user_id"] = form.get_user().pk
            request.session.modified = True
            return redirect("accounts:login_totp")

        user = form.get_user()
        if user and user.is_active:
            _register_login_success(user, request)
            return redirect("accounts:perfil")
        if user and not user.is_active:
            messages.error(request, _("Conta inativa. Verifique seu e-mail para ativá-la."))
        else:
            messages.error(request, _("Credenciais inválidas."))

    return render(request, "login/login.html", {"form": form})


@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def login_totp(request):
    if request.user.is_authenticated:
        return redirect("accounts:perfil")

    user = _get_pending_2fa_user(request)
    if not user:
        return redirect("accounts:login")

    form = TotpLoginForm(user, request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        _clear_pending_2fa(request)
        _register_login_success(user, request)
        return redirect("accounts:perfil")

    return render(request, "login/totp.html", {"form": form, "email": user.email})


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


def conta_inativa(request):
    """Exibe aviso para usuários inativos e encerra a sessão."""
    if request.user.is_authenticated:
        logout(request)
    return render(request, "account_inactive.html")


ACCOUNT_DELETE_CONFIRMATION_TOKEN = "EXCLUIR"


@login_required
def excluir_conta(request):
    """Permite que o usuário exclua sua própria conta."""

    target_user = _resolve_management_target_user(request)
    is_self = target_user == request.user
    is_htmx = bool(request.headers.get("HX-Request"))

    active_delete_error = _(
        "Apenas contas inativas podem ser excluídas definitivamente. Desative a conta antes de continuar."
    )

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

    def _redirect_to_profile():
        url = reverse("accounts:perfil")
        if not is_self:
            params = {"public_id": str(target_user.public_id)}
            if target_user.username:
                params["username"] = target_user.username
            url = f"{url}?{urlencode(params)}"
        return redirect(url)

    def _render_form(status: int = 200, **extra_context):
        context = {
            "target_user": target_user,
            "is_self": is_self,
            "confirmation_token": ACCOUNT_DELETE_CONFIRMATION_TOKEN,
        }
        context.update(extra_context)
        template_name = (
            "accounts/partials/account_delete_modal.html"
            if is_htmx
            else "accounts/delete_account_confirm.html"
        )
        return render(request, template_name, context, status=status)

    if target_user.is_active:
        if is_htmx:
            return _render_form(status=400, error_message=active_delete_error)
        messages.error(request, active_delete_error)
        return _redirect_to_profile()

    if request.method == "GET":
        return _render_form()

    if request.method != "POST":
        if is_htmx:
            return _render_form(status=405)
        return _redirect_to_form()

    confirm_value = request.POST.get("confirm", "")
    if confirm_value != ACCOUNT_DELETE_CONFIRMATION_TOKEN:
        error_message = _("Confirme digitando EXCLUIR.")
        if is_htmx:
            return _render_form(
                status=400,
                error_message=error_message,
                confirm_value=confirm_value,
            )
        messages.error(request, error_message)
        return _redirect_to_form()

    with transaction.atomic():
        user = target_user
        user.exclusao_confirmada = True
        user.is_active = False
        user.save(update_fields=["exclusao_confirmada", "is_active"])
        user.delete()
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

    if is_self and token:
        send_cancel_delete_email.delay(token.id)

    if is_self:
        logout(request)
        messages.success(
            request,
            _("Sua conta foi excluída com sucesso. Você pode reativá-la em até 30 dias."),
        )
        redirect_url = reverse("core:home")
    else:
        messages.success(
            request,
            _("Conta de %(username)s excluída com sucesso.")
            % {"username": target_user.get_full_name()},
        )
        redirect_url = reverse("membros:membros_lista")

    if is_htmx:
        response = HttpResponse(status=204)
        response["HX-Redirect"] = redirect_url
        return response

    return redirect(redirect_url)


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
                ).update(used_at=timezone.now(), status=AccountToken.Status.UTILIZADO)
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

    if request.method != "POST" and token.status == AccountToken.Status.PENDENTE:
        token.mark_confirmed()

    if request.method == "POST":
        form = SetPasswordForm(token.usuario, request.POST)
        if form.is_valid():
            form.save()
            user = token.usuario
            cache.delete(f"failed_login_attempts_user_{user.pk}")
            cache.delete(f"lockout_user_{user.pk}")
            token.mark_used()
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
    base_context = {
        "status": "erro",
        "message": _("Link inválido ou expirado."),
    }
    try:
        token_obj = AccountToken.objects.select_related("usuario").get(
            codigo=token,
            tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        )
    except AccountToken.DoesNotExist:
        return render(request, "accounts/email_confirm.html", base_context)

    SecurityEvent.objects.create(
        usuario=token_obj.usuario,
        evento="email_confirmacao_link_acessado",
        ip=get_client_ip(request),
    )

    if token_obj.used_at:
        context = {
            "status": "expirado",
            "message": _("Este link já foi utilizado. Solicite um novo e-mail de confirmação."),
        }
        SecurityEvent.objects.create(
            usuario=token_obj.usuario,
            evento="email_confirmacao_falha",
            ip=get_client_ip(request),
        )
        return render(request, "accounts/email_confirm.html", context)
    if token_obj.expires_at < timezone.now() or token_obj.used_at:
        SecurityEvent.objects.create(
            usuario=token_obj.usuario,
            evento="email_confirmacao_falha",
            ip=get_client_ip(request),
        )
        return render(
            request,
            "accounts/email_confirm.html",
            {
                "status": "expirado",
                "message": _(
                    "Seu link expirou. Solicite um novo e-mail de confirmação para continuar."
                ),
            },
        )

    with transaction.atomic():
        user = token_obj.usuario
        user.is_active = True
        user.email_confirmed = True
        user.save(update_fields=["is_active", "email_confirmed"])
        token_obj.mark_used()
        SecurityEvent.objects.create(
            usuario=user,
            evento="email_confirmado",
            ip=get_client_ip(request),
        )
    return render(
        request,
        "accounts/email_confirm_success.html",
        {
            "status": "sucesso",
            "message": _("Seu e-mail foi confirmado com sucesso."),
        },
    )


def confirm_email(request):
    """Aceita tokens via querystring e delega para ``confirmar_email``."""

    token = request.GET.get("token")
    if not token:
        return render(
            request,
            "accounts/email_confirm.html",
            {
                "status": "erro",
                "message": _("Token não fornecido na URL."),
            },
        )

    return confirmar_email(request, token)

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
        token_obj.mark_used()
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
                ).update(used_at=timezone.now(), status=AccountToken.Status.UTILIZADO)
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
        valor = (request.POST.get("cpf") or "").strip()
        cnpj_input = (request.POST.get("cnpj") or "").strip()
        if not valor and not cnpj_input:
            messages.error(request, IDENTIFIER_REQUIRED_ERROR)
            return redirect("accounts:cpf")

        normalized_cnpj = ""
        if cnpj_input:
            try:
                normalized_cnpj = validate_cnpj(cnpj_input)
            except ValidationError as exc:
                message = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
                messages.error(request, message or _("CNPJ inválido."))
                return redirect("accounts:cpf")
            if User.objects.filter(cnpj=normalized_cnpj).exists():
                messages.error(request, _("CNPJ já cadastrado."))
                return redirect("accounts:cpf")

        if valor:
            try:
                cpf_validator(valor)
            except ValidationError:
                messages.error(request, "CPF inválido.")
                return redirect("accounts:cpf")

            matches = User.objects.filter(cpf=valor)
            requires_cnpj = matches.filter(Q(cnpj__isnull=True) | Q(cnpj="")).exists()
            if requires_cnpj:
                messages.error(request, CPF_REUSE_ERROR)
                return redirect("accounts:cpf")

            cnpj_required = matches.exists()
            if cnpj_required and not normalized_cnpj:
                messages.error(request, CPF_REUSE_ERROR)
                return redirect("accounts:cpf")

            request.session["cpf"] = valor
            if normalized_cnpj:
                request.session["cnpj"] = normalized_cnpj
            elif cnpj_required:
                request.session.pop("cnpj", None)

            if cnpj_required:
                request.session["require_cnpj"] = True
            else:
                request.session.pop("require_cnpj", None)
        else:
            request.session.pop("cpf", None)
            request.session.pop("require_cnpj", None)
            if normalized_cnpj:
                request.session["cnpj"] = normalized_cnpj
            else:
                request.session.pop("cnpj", None)

        return redirect("accounts:email")
    return render(request, "register/cpf.html")


def email(request):
    prefilled_email = request.session.get("email", "")
    email_locked = bool(request.session.get("invite_email"))

    if request.method == "POST":
        val = request.POST.get("email")
        if val:
            if email_locked and prefilled_email and val.lower() != prefilled_email.lower():
                messages.error(request, _("O e-mail confirmado não pode ser alterado."))
                return redirect("accounts:email")
            if User.objects.filter(email__iexact=val).exists():
                messages.error(request, _("Este e-mail já está em uso."))
                return redirect("accounts:email")
            else:
                request.session["email"] = val
                return redirect("accounts:senha")
    context = {
        "prefilled_email": prefilled_email,
        "email_locked": email_locked,
        "email_attrs": 'readonly="readonly"' if email_locked else "",
    }
    return render(request, "register/email.html", context)


@require_GET
def confirmar_convite(request):
    token_code = (request.GET.get("token") or "").strip()
    email = (request.GET.get("email") or "").strip()

    if not token_code or not email:
        messages.error(request, _("Link de confirmação inválido."))
        return redirect("tokens:token")

    preregistro = (
        PreRegistroConvite.objects.select_related("token")
        .filter(email__iexact=email, codigo=token_code)
        .first()
    )
    agora = timezone.now()

    if not preregistro or preregistro.status != PreRegistroConvite.Status.ENVIADO:
        messages.error(request, _("Convite inválido ou já utilizado."))
        return redirect("tokens:token")

    token_obj = preregistro.token
    if (
        token_obj.estado != TokenAcesso.Estado.NOVO
        or (token_obj.data_expiracao and token_obj.data_expiracao < agora)
    ):
        messages.error(request, _("Token expirado ou inválido."))
        return redirect("tokens:token")

    request.session["invite_token"] = token_code
    request.session["email"] = email
    request.session["invite_email"] = email
    if preregistro.evento_id:
        request.session["invite_event_id"] = str(preregistro.evento_id)

    query = urlencode({"token": token_code, "email": email})
    return redirect(f"{reverse('tokens:token')}?{query}")


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
            token_obj = find_token_by_code(token_code)
        except TokenAcesso.DoesNotExist:
            messages.error(request, "Token inválido.")
            return redirect("tokens:token")
        if token_obj.estado != TokenAcesso.Estado.NOVO:
            messages.error(request, "Token inválido.")
            return redirect("tokens:token")
        invite_event_id = request.session.get("invite_event_id")
        invite_event = None
        if invite_event_id:
            invite_event = (
                Evento.objects.select_related("organizacao")
                .filter(pk=invite_event_id)
                .first()
            )
            if not invite_event or (
                token_obj.organizacao_id
                and invite_event.organizacao_id != token_obj.organizacao_id
            ):
                messages.error(request, _("Convite inválido para este evento."))
                return redirect("tokens:token")
            if invite_event.publico_alvo != 0:
                messages.error(
                    request,
                    _("O evento não está disponível para inscrições de convidados."),
                )
                return redirect("tokens:token")
        if token_obj.data_expiracao and token_obj.data_expiracao < timezone.now():
            token_obj.estado = TokenAcesso.Estado.EXPIRADO
            token_obj.save(update_fields=["estado"])
            messages.error(request, "Token expirado.")
            return redirect("tokens:token")

        username = request.session.get("usuario")
        email_val = request.session.get("email")
        pwd_hash = request.session.get("senha_hash")
        cpf_val = request.session.get("cpf")
        cnpj_val = request.session.get("cnpj")
        require_cnpj = request.session.get("require_cnpj")

        if require_cnpj and not cnpj_val:
            messages.error(request, CPF_REUSE_ERROR)
            return redirect("accounts:cpf")
        contato = (request.session.get("nome") or "").strip()

        if username and pwd_hash:
            if token_obj.tipo_destino != TokenAcesso.TipoUsuario.CONVIDADO:
                messages.error(request, _("Convite inválido."))
                return redirect("tokens:token")
            mapped_user_type = UserType.CONVIDADO
            convite_nucleo = (
                ConviteNucleo.objects.select_related("nucleo__organizacao")
                .filter(token_obj=token_obj)
                .first()
            )
            organizacao = None
            nucleo = None
            if convite_nucleo and convite_nucleo.nucleo_id:
                nucleo = convite_nucleo.nucleo
                organizacao = convite_nucleo.nucleo.organizacao
            else:
                organizacao = token_obj.organizacao
            try:
                with transaction.atomic():
                    user = User.objects.create(
                        username=username,
                        email=email_val,
                        contato=contato,
                        password=pwd_hash,
                        cpf=cpf_val,
                        cnpj=cnpj_val,
                        user_type=mapped_user_type,
                        is_active=False,
                        email_confirmed=False,
                        organizacao=organizacao,
                        nucleo=nucleo,
                    )
            except IntegrityError:
                messages.error(
                    request,
                    _("Nome de usuário já cadastrado."),
                )
                request.session.pop("usuario", None)
                logger.warning(
                    "accounts.registro.integrity_error",
                    extra={
                        "username": username,
                        "email": email_val,
                        "token": token_code,
                        "ip": get_client_ip(request),
                    },
                )
                return redirect("accounts:usuario")

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
            SecurityEvent.objects.create(
                usuario=user,
                evento="registro_sucesso",
                ip=get_client_ip(request),
            )

            request.session["termos"] = True
            request.session.pop("cnpj", None)
            request.session.pop("require_cnpj", None)
            if invite_event:
                user.backend = "django.contrib.auth.backends.ModelBackend"
                login(request, user)
                request.session.pop("invite_token", None)
                request.session.pop("invite_event_id", None)
                request.session.pop("invite_email", None)
                return redirect("eventos:inscricao_criar", pk=invite_event.pk)

            return render(request, "register/registro_sucesso.html")

        messages.error(request, "Erro ao criar usuário. Tente novamente.")
        logger.warning(
            "accounts.registro.falha",
            extra={
                "token": token_code,
                "username": username,
                "email": email_val,
                "ip": get_client_ip(request),
            },
        )
        return redirect("accounts:usuario")

    return render(request, "register/termos.html")


def registro_sucesso(request):
    return render(request, "register/registro_sucesso.html")


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
