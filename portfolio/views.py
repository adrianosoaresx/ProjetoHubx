from __future__ import annotations

from collections import Counter

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.utils import resolve_back_href

from accounts.models import UserMedia, UserType

from .forms import MediaForm, PortfolioFilterForm


def _media_counts_for(user) -> dict[str, int]:
    medias = list(user.medias.all())
    counter = Counter(media.media_type for media in medias)
    total = len(medias)
    return {
        "total": total,
        "images": counter.get("image", 0),
        "videos": counter.get("video", 0),
        "pdfs": counter.get("pdf", 0),
        "others": counter.get("other", 0),
    }


def _deny_guest_portfolio_access(request: HttpRequest) -> None:
    user_type = getattr(request.user, "user_type", None)
    if isinstance(user_type, UserType):
        user_type = user_type.value

    if user_type == UserType.CONVIDADO.value:
        raise PermissionDenied(_("Portfólio não está disponível para usuários convidados."))


@login_required
def list_portfolio(request: HttpRequest) -> HttpResponse:
    _deny_guest_portfolio_access(request)

    show_form = request.GET.get("adicionar") == "1" or request.method == "POST"

    filter_form = PortfolioFilterForm(request.GET or None)
    q = ""
    if filter_form.is_valid():
        q = filter_form.cleaned_data.get("q", "") or ""

    if request.method == "POST":
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.user = request.user
            media.save()
            form.save_m2m()
            messages.success(request, _("Arquivo enviado com sucesso."))
            return redirect("portfolio:index")
    else:
        form = MediaForm()

    allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
    form.fields["file"].widget.attrs["accept"] = ",".join(allowed_exts)
    form.fields["file"].help_text = _("Selecione um arquivo")
    form.fields["descricao"].help_text = _("Breve descrição do portfólio")

    medias_qs = (
        request.user.medias.select_related("user").prefetch_related("tags").order_by("-created_at")
    )
    if q:
        medias_qs = medias_qs.filter(
            Q(descricao__icontains=q) | Q(tags__nome__icontains=q)
        ).distinct()

    medias = list(medias_qs)

    counts = _media_counts_for(request.user)

    context = {
        "form": form,
        "medias": medias,
        "show_form": show_form,
        "filter_form": filter_form,
        "q": q,
        "is_owner": True,
        "counts": counts,
        "hero_title": _("Portfólio"),
        "hero_subtitle": _("Gerencie suas imagens, vídeos e documentos"),
    }

    return render(request, "portfolio/list.html", context)


@login_required
def detail(request: HttpRequest, pk: int) -> HttpResponse:
    _deny_guest_portfolio_access(request)

    media = get_object_or_404(UserMedia, pk=pk, user=request.user)

    counts = _media_counts_for(request.user)

    context = {
        "media": media,
        "back_url": resolve_back_href(
            request,
            fallback=reverse("portfolio:index"),
            disallow={request.path},
        ),
        "counts": counts,
        "hero_title": media.descricao or _("Detalhes do portfólio"),
        "hero_subtitle": _("Visualize sua mídia em destaque"),
    }
    return render(request, "portfolio/detail.html", context)


@login_required
def edit(request: HttpRequest, pk: int) -> HttpResponse:
    _deny_guest_portfolio_access(request)

    media = get_object_or_404(UserMedia, pk=pk, user=request.user)

    if request.method == "POST":
        form = MediaForm(request.POST, request.FILES, instance=media)
        if form.is_valid():
            form.save()
            messages.success(request, _("Portfólio atualizado com sucesso."))
            return redirect("portfolio:index")
    else:
        form = MediaForm(instance=media)

    allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
    form.fields["file"].widget.attrs["accept"] = ",".join(allowed_exts)
    form.fields["file"].help_text = _("Selecione um arquivo")
    form.fields["descricao"].help_text = _("Breve descrição do portfólio")

    counts = _media_counts_for(request.user)

    context = {
        "form": form,
        "media": media,
        "counts": counts,
        "hero_title": _("Editar Portfólio"),
        "hero_subtitle": media.descricao,
        "back_url": resolve_back_href(
            request,
            fallback=reverse("portfolio:index"),
            disallow={request.path},
        ),
    }
    return render(request, "portfolio/form.html", context)


@login_required
def delete(request: HttpRequest, pk: int) -> HttpResponse:
    _deny_guest_portfolio_access(request)

    media = get_object_or_404(UserMedia, pk=pk, user=request.user)

    if request.method == "POST":
        media.delete(soft=False)
        messages.success(request, _("Item do portfólio removido."))
        return redirect("portfolio:index")

    hx_target = request.headers.get("HX-Target", "")
    if hx_target == "modal":
        return render(
            request,
            "portfolio/delete_modal.html",
            {
                "media": media,
                "titulo": _("Remover item do portfólio"),
                "mensagem": _("Tem certeza que deseja remover este item do portfólio?"),
                "submit_label": _("Remover"),
                "form_action": reverse("portfolio:delete", args=[media.pk]),
            },
        )

    counts = _media_counts_for(request.user)

    context = {
        "media": media,
        "counts": counts,
        "hero_title": _("Remover Portfólio"),
        "hero_subtitle": media.descricao,
        "back_url": resolve_back_href(
            request,
            fallback=reverse("portfolio:index"),
            disallow={request.path},
        ),
    }
    return render(request, "portfolio/confirm_delete.html", context)
