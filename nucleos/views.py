from __future__ import annotations

import logging

from collections import Counter
from typing import Iterable, Mapping

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from accounts.models import UserType
from core.cache import get_cache_version
from core.permissions import (
    AdminOperatorOrCoordinatorRequiredMixin,
    AdminOrOperatorRequiredMixin,
    AdminRequiredMixin,
    GerenteRequiredMixin,
    NoSuperadminMixin,
)
from core.utils import resolve_back_href
from eventos.models import Evento

from .forms import (
    NucleoForm,
    NucleoMediaForm,
    NucleoPortfolioFilterForm,
    NucleoSearchForm,
    ParticipacaoDecisaoForm,
)
from .models import CoordenadorSuplente, Nucleo, NucleoMidia, ParticipacaoNucleo
from .tasks import notify_participacao_aprovada, notify_participacao_recusada

logger = logging.getLogger(__name__)

User = get_user_model()


def _user_has_consultoria_access(user) -> bool:
    tipo = getattr(user, "get_tipo_usuario", None)
    if tipo == UserType.CONSULTOR.value:
        return True

    user_type = getattr(user, "user_type", None)
    if user_type in {UserType.CONSULTOR, UserType.CONSULTOR.value}:
        return True

    nucleos_consultoria = getattr(user, "nucleos_consultoria", None)
    if nucleos_consultoria is not None:
        try:
            return nucleos_consultoria.filter(deleted=False).exists()
        except Exception:  # pragma: no cover - defensive
            pass
    return False


def _get_consultor_nucleo_ids(user) -> set[int]:
    nucleo_ids: set[int] = set()

    nucleos_consultoria = getattr(user, "nucleos_consultoria", None)
    if nucleos_consultoria is not None:
        try:
            nucleo_ids.update(pk for pk in nucleos_consultoria.values_list("id", flat=True) if pk)
        except Exception:  # pragma: no cover - defensive
            pass

    participacoes = getattr(user, "participacoes", None)
    if participacoes is not None:
        participacao_ids = participacoes.filter(
            status="ativo",
            status_suspensao=False,
        ).values_list("nucleo_id", flat=True)
        nucleo_ids.update(pk for pk in participacao_ids if pk)

    nucleo_id = getattr(user, "nucleo_id", None)
    if nucleo_id:
        nucleo_ids.add(nucleo_id)

    return nucleo_ids


def _get_allowed_classificacao_keys(user) -> set[str]:
    all_keys = {choice.value for choice in Nucleo.Classificacao}
    tipo = getattr(user, "get_tipo_usuario", None)

    if tipo in {
        UserType.ADMIN.value,
        UserType.OPERADOR.value,
        UserType.ROOT.value,
    }:
        return all_keys

    if _user_has_consultoria_access(user):
        return all_keys

    return {Nucleo.Classificacao.CONSTITUIDO.value}


class NucleoVisibilityMixin:
    def get_allowed_classificacao_keys(self) -> set[str]:
        if not hasattr(self, "_allowed_classificacao_keys"):
            self._allowed_classificacao_keys = _get_allowed_classificacao_keys(self.request.user)
        return self._allowed_classificacao_keys

    def user_has_consultoria_access(self) -> bool:
        if not hasattr(self, "_user_has_consultoria_access"):
            self._user_has_consultoria_access = _user_has_consultoria_access(self.request.user)
        return self._user_has_consultoria_access

    def get_consultor_nucleo_ids(self) -> set[int]:
        if not hasattr(self, "_consultor_nucleo_ids"):
            self._consultor_nucleo_ids = _get_consultor_nucleo_ids(self.request.user)
        return self._consultor_nucleo_ids


def _nucleo_portfolio_counts(medias: Iterable[NucleoMidia]) -> dict[str, int]:
    medias_list = list(medias)
    counts = Counter(media.media_type for media in medias_list)
    counts["total"] = len(medias_list)
    return counts


def _configure_nucleo_portfolio_form_fields(form: NucleoMediaForm) -> None:
    allowed_exts = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
    file_field = form.fields.get("file")
    if file_field is not None:
        file_field.widget.attrs["accept"] = ",".join(allowed_exts)
        file_field.help_text = _("Selecione um arquivo")
    descricao_field = form.fields.get("descricao")
    if descricao_field is not None:
        descricao_field.help_text = _("Breve descrição do portfólio")


def _usuario_pode_gerenciar_portfolio_nucleo(user, nucleo: Nucleo) -> bool:
    tipo_usuario = getattr(user, "user_type", None)
    if tipo_usuario in {UserType.ADMIN.value, UserType.OPERADOR.value}:
        return True
    if user.has_perm("nucleos.change_nucleo"):
        return True
    participacoes = getattr(user, "participacoes", None)
    if participacoes is not None:
        return participacoes.filter(
            nucleo=nucleo,
            papel="coordenador",
            status="ativo",
            status_suspensao=False,
        ).exists()
    return False


NUCLEO_SECTION_CONFIG: list[dict[str, object]] = [
    {
        "key": Nucleo.Classificacao.CONSTITUIDO.value,
        "title": _("Núcleos constituídos"),
        "icon": "building-2",
        "icon_classes": "flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-success-500)]/10 text-[var(--color-success-600)] shadow-lg shadow-[var(--color-success-500)]/15",
        "empty_message": _("Nenhum núcleo constituído encontrado."),
        "aria_label": _("Lista de núcleos constituídos"),
    },
    {
        "key": Nucleo.Classificacao.PLANEJAMENTO.value,
        "title": _("Núcleos em planejamento"),
        "icon": "clipboard-list",
        "icon_classes": "flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-warning-500)]/10 text-[var(--color-warning-600)] shadow-lg shadow-[var(--color-warning-500)]/20",
        "empty_message": _("Nenhum núcleo em planejamento encontrado."),
        "aria_label": _("Lista de núcleos em planejamento"),
    },
    {
        "key": Nucleo.Classificacao.EM_FORMACAO.value,
        "title": _("Núcleos em formação"),
        "icon": "sparkles",
        "icon_classes": "flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-info-500)]/10 text-[var(--color-info-600)] shadow-lg shadow-[var(--color-info-500)]/20",
        "empty_message": _("Nenhum núcleo em formação encontrado."),
        "aria_label": _("Lista de núcleos em formação"),
    },
]


def build_nucleo_sections(
    current_items: Iterable[Nucleo],
    totals_by_classificacao: Mapping[str, int],
    allowed_keys: Iterable[str],
) -> list[dict[str, object]]:
    allowed_set = set(allowed_keys)
    grouped: dict[str, list[Nucleo]] = {key: [] for key in allowed_set}

    for nucleo in current_items:
        if nucleo.classificacao in allowed_set:
            grouped.setdefault(nucleo.classificacao, []).append(nucleo)

    sections: list[dict[str, object]] = []
    for config in NUCLEO_SECTION_CONFIG:
        key = config["key"]
        if key not in allowed_set:
            continue
        items = grouped.get(key, [])
        total = totals_by_classificacao.get(key)
        if total is None:
            total = len(items)
        section = {
            **config,
            "items": items,
            "total": total,
        }
        sections.append(section)

    return sections


class NucleoPainelRenderMixin:
    painel_template_name = "nucleos/detail.html"
    partial_template_name: str | None = None

    def get_partial_template_name(self) -> str:
        return self.partial_template_name or self.template_name

    def render_to_response(self, context, **response_kwargs):  # type: ignore[override]
        is_htmx_request = self.request.headers.get("HX-Request") == "true"
        context["is_htmx"] = is_htmx_request
        if is_htmx_request:
            return super().render_to_response(context, **response_kwargs)

        context["partial_template"] = self.get_partial_template_name()
        return TemplateResponse(self.request, self.painel_template_name, context)


class NucleoListView(NoSuperadminMixin, LoginRequiredMixin, NucleoVisibilityMixin, ListView):
    model = Nucleo
    template_name = "nucleos/nucleo_list.html"
    paginate_by = 10

    def get_classificacao(self) -> str | None:
        if hasattr(self, "_classificacao"):
            return self._classificacao

        allowed_choices = self.get_allowed_classificacao_keys()
        classificacao = self.request.GET.get("classificacao")
        if classificacao not in allowed_choices:
            classificacao = None

        self._classificacao = classificacao
        return classificacao

    def get_queryset(self):
        if hasattr(self, "_cached_queryset"):
            return self._cached_queryset

        user = self.request.user
        q = self.request.GET.get("q", "")
        allowed_keys = self.get_allowed_classificacao_keys()
        classificacao = self.get_classificacao()
        version = get_cache_version("nucleos_list")
        allowed_fragment = ",".join(sorted(allowed_keys)) or "_"
        cache_key = (
            f"nucleos_list:v{version}:{user.id}:{allowed_fragment}:{q}:{classificacao or 'all'}"
        )

        base_qs = (
            Nucleo.objects.select_related("organizacao")
            .prefetch_related("participacoes")
            .annotate(
                membros_count=Count(
                    "participacoes",
                    filter=Q(
                        participacoes__status="ativo",
                        participacoes__status_suspensao=False,
                    ),
                    distinct=True,
                )
            )
        )

        qs = base_qs.filter(deleted=False, classificacao__in=allowed_keys)

        tipo_usuario = getattr(user, "get_tipo_usuario", None)
        if tipo_usuario == UserType.ADMIN.value:
            qs = qs.filter(organizacao=user.organizacao)
        elif tipo_usuario == UserType.COORDENADOR.value:
            qs = qs.filter(participacoes__user=user)
        elif tipo_usuario in {UserType.ASSOCIADO.value, UserType.NUCLEADO.value}:
            qs = qs.filter(organizacao=user.organizacao)
        elif self.user_has_consultoria_access():
            consultor_ids = self.get_consultor_nucleo_ids()
            if consultor_ids:
                qs = qs.filter(pk__in=consultor_ids)
            else:
                qs = qs.none()

        if q:
            qs = qs.filter(nome__icontains=q)

        # Armazena um queryset com os mesmos filtros aplicados para ser usado na
        # contagem dos cartões de classificação. O ``distinct()`` garante que
        # núcleos não sejam contabilizados mais de uma vez quando há múltiplas
        # participações relacionadas ao mesmo usuário.
        self._qs_for_counts = qs.distinct()

        cached_ids = cache.get(cache_key)
        if cached_ids is not None:
            result = list(
                base_qs.filter(pk__in=cached_ids, classificacao__in=allowed_keys).order_by("nome")
            )
            self._cached_queryset = result
            return result

        if classificacao:
            qs = qs.filter(classificacao=classificacao)

        ids = list(qs.order_by("nome").distinct().values_list("pk", flat=True))
        cache.set(cache_key, ids, 300)

        result = list(
            base_qs.filter(pk__in=ids, classificacao__in=allowed_keys).order_by("nome")
        )
        self._cached_queryset = result
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("list_title", _("Núcleos"))
        ctx.setdefault("list_aria_label", _("Lista de núcleos"))
        ctx.setdefault("empty_message", _("Nenhum núcleo encontrado."))
        ctx.setdefault("list_hero_template", "_components/hero_nucleo.html")
        ctx.setdefault("list_hero_action_template", "nucleos/hero_actions_nucleo.html")
        ctx.setdefault("list_card_template", "_components/card_nucleo.html")
        ctx.setdefault("item_context_name", "nucleo")
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        show_totals = self.request.user.user_type in {UserType.ADMIN, UserType.OPERADOR}
        ctx["show_totals"] = show_totals

        allowed_keys = self.get_allowed_classificacao_keys()
        ctx["allowed_classificacao_keys"] = sorted(allowed_keys)

        # Totais: número de núcleos e membros ativos na organização do usuário
        qs = self.get_queryset()

        if show_totals:
            ctx["total_nucleos"] = len(qs)
            nucleo_ids = [n.pk for n in qs]
            # contar membros ativos (sem suspensão) somando participações únicas por usuário
            from .models import ParticipacaoNucleo

            ctx["total_membros_org"] = (
                ParticipacaoNucleo.objects.filter(nucleo_id__in=nucleo_ids, status="ativo", status_suspensao=False)
                .values("user")
                .distinct()
                .count()
            )
            # totais de eventos (todos os status) e por status (0=Ativo, 1=Concluído)
            ctx["total_eventos_org"] = Evento.objects.filter(nucleo_id__in=nucleo_ids).count()
            ctx["total_eventos_planejamento_org"] = Evento.objects.filter(
                nucleo_id__in=nucleo_ids,
                status=Evento.Status.PLANEJAMENTO,
            ).count()
            ctx["total_eventos_ativos_org"] = Evento.objects.filter(
                nucleo_id__in=nucleo_ids,
                status=Evento.Status.ATIVO,
            ).count()
            ctx["total_eventos_concluidos_org"] = Evento.objects.filter(
                nucleo_id__in=nucleo_ids,
                status=Evento.Status.CONCLUIDO,
            ).count()
        else:
            ctx["total_nucleos"] = None
            ctx["total_membros_org"] = None
            ctx["total_eventos_org"] = None
            ctx["total_eventos_planejamento_org"] = None
            ctx["total_eventos_ativos_org"] = None
            ctx["total_eventos_concluidos_org"] = None
        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
        ctx["querystring"] = urlencode(params, doseq=True)

        selected_classificacao = self.get_classificacao()
        ctx["selected_classificacao"] = selected_classificacao
        ctx["is_all_classificacao_active"] = selected_classificacao is None

        params_without_page = self.request.GET.copy()
        params_without_page.pop("page", None)
        params_without_classificacao = params_without_page.copy()
        params_without_classificacao.pop("classificacao", None)

        base_url = self.request.path
        if params_without_classificacao:
            base_query = params_without_classificacao.urlencode()
            ctx["nucleos_reset_url"] = f"{base_url}?{base_query}"
        else:
            ctx["nucleos_reset_url"] = base_url

        def card_extra_attributes(url: str):
            return format_html(
                'data-href="{}" onclick="window.location.href=this.dataset.href"', url
            )

        ctx["nucleos_reset_extra_attributes"] = card_extra_attributes(ctx["nucleos_reset_url"])

        classificacao_filters: list[dict[str, object]] = []

        if show_totals:
            base_qs = getattr(self, "_qs_for_counts", Nucleo.objects.none())
            counts = {key: 0 for key in allowed_keys}
            for row in base_qs.values("classificacao").annotate(total=Count("id", distinct=True)):
                key = row["classificacao"]
                if key in counts:
                    counts[key] = row["total"]

            classificacao_labels = [
                (Nucleo.Classificacao.EM_FORMACAO.value, _("Formação")),
                (Nucleo.Classificacao.PLANEJAMENTO.value, _("Planejamento")),
                (Nucleo.Classificacao.CONSTITUIDO.value, _("Constituído")),
            ]

            for classificacao, label in classificacao_labels:
                if classificacao not in allowed_keys:
                    continue
                params_for_filter = params_without_classificacao.copy()
                params_for_filter["classificacao"] = classificacao
                filter_query = params_for_filter.urlencode()
                filter_url = f"{base_url}?{filter_query}" if filter_query else base_url
                classificacao_filters.append(
                    {
                        "value": classificacao,
                        "label": label,
                        "count": counts.get(classificacao, 0),
                        "url": filter_url,
                        "is_active": selected_classificacao == classificacao,
                        "extra_attributes": card_extra_attributes(filter_url),
                    }
                )

        ctx["classificacao_filters"] = classificacao_filters

        base_qs_for_totals = getattr(self, "_qs_for_counts", Nucleo.objects.none())
        classificacao_totals: dict[str, int] = {key: 0 for key in allowed_keys}

        if hasattr(base_qs_for_totals, "values"):
            for row in base_qs_for_totals.values("classificacao").annotate(total=Count("id", distinct=True)):
                key = row["classificacao"]
                if key in classificacao_totals:
                    classificacao_totals[key] = row["total"]

        ctx["classificacao_totals"] = classificacao_totals
        ctx["nucleo_sections"] = build_nucleo_sections(
            list(ctx.get("object_list", [])), classificacao_totals, allowed_keys
        )

        return ctx


class NucleoMeusView(NoSuperadminMixin, LoginRequiredMixin, NucleoVisibilityMixin, ListView):
    model = Nucleo
    # Reutiliza o template padrão de listagem de núcleos para evitar duplicação
    template_name = "nucleos/nucleo_list.html"
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type == UserType.ADMIN:
            return redirect("nucleos:list")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if hasattr(self, "_cached_queryset"):
            return self._cached_queryset

        user = self.request.user
        q = self.request.GET.get("q", "")
        allowed_keys = self.get_allowed_classificacao_keys()
        version = get_cache_version("nucleos_meus")
        allowed_fragment = ",".join(sorted(allowed_keys)) or "_"
        cache_key = f"nucleos_meus:v{version}:{user.id}:{allowed_fragment}:{q}"
        cached_ids = cache.get(cache_key)

        base_qs = (
            Nucleo.objects.select_related("organizacao")
            .prefetch_related("participacoes")
            .annotate(
                membros_count=Count(
                    "participacoes",
                    filter=Q(
                        participacoes__status="ativo",
                        participacoes__status_suspensao=False,
                    ),
                    distinct=True,
                )
            )
        )

        if cached_ids is not None:
            qs = base_qs.filter(pk__in=cached_ids, classificacao__in=allowed_keys).order_by("nome")
            result = list(qs)
            self._cached_queryset = result
            return result

        qs = base_qs.filter(
            deleted=False,
            participacoes__user=user,
            participacoes__status="ativo",
            participacoes__status_suspensao=False,
            classificacao__in=allowed_keys,
        )

        if q:
            qs = qs.filter(nome__icontains=q)

        ids = list(qs.order_by("nome").distinct().values_list("pk", flat=True))
        cache.set(cache_key, ids, 300)

        result = list(
            base_qs.filter(pk__in=ids, classificacao__in=allowed_keys).order_by("nome")
        )
        self._cached_queryset = result
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        # Ajusta títulos e rótulos para o contexto "Meus Núcleos"
        ctx.setdefault("list_title", _("Meus Núcleos"))
        ctx.setdefault("list_aria_label", _("Lista de núcleos do usuário"))
        ctx.setdefault("empty_message", _("Nenhum núcleo encontrado."))
        # Usa o mesmo hero padrão, apenas trocando o título
        ctx.setdefault("list_hero_template", "_components/hero_nucleo.html")
        # Mantém as ações do hero iguais às da listagem principal
        ctx.setdefault("list_hero_action_template", "nucleos/hero_actions_nucleo.html")
        ctx.setdefault("list_card_template", "_components/card_nucleo.html")
        ctx.setdefault("item_context_name", "nucleo")
        ctx.setdefault("show_totals", False)
        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
        ctx["querystring"] = urlencode(params, doseq=True)
        allowed_keys = self.get_allowed_classificacao_keys()
        ctx["allowed_classificacao_keys"] = sorted(allowed_keys)
        current_items = list(ctx.get("object_list", []))
        all_items = list(self.get_queryset())
        counts = Counter(
            nucleo.classificacao for nucleo in all_items if nucleo.classificacao in allowed_keys
        )
        classificacao_totals: dict[str, int] = {}
        for config in NUCLEO_SECTION_CONFIG:
            key = config["key"]
            if key in allowed_keys:
                classificacao_totals[key] = counts.get(key, 0)
        ctx["classificacao_totals"] = classificacao_totals
        ctx["nucleo_sections"] = build_nucleo_sections(
            current_items, classificacao_totals, allowed_keys
        )

        return ctx


class NucleoCreateView(
    NoSuperadminMixin, AdminOrOperatorRequiredMixin, LoginRequiredMixin, CreateView
):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/nucleo_form.html"
    success_url = reverse_lazy("nucleos:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fallback_url = str(self.success_url)
        back_href = resolve_back_href(
            self.request,
            fallback=fallback_url,
        )
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        return context

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, _("Núcleo criado com sucesso."))
        response = super().form_valid(form)
        # Se a submissão vier via HTMX (ex.: hx-boost/hx-post), informe o redirecionamento explícito
        if self.request.headers.get("HX-Request"):
            resp = HttpResponse(status=204)
            resp["HX-Redirect"] = str(self.get_success_url())
            return resp
        return response


class NucleoUpdateView(
    NoSuperadminMixin,
    AdminOperatorOrCoordinatorRequiredMixin,
    LoginRequiredMixin,
    UpdateView,
):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/nucleo_form.html"
    success_url = reverse_lazy("nucleos:list")
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nucleo = context.get("object") or getattr(self, "object", None)
        if nucleo:
            fallback_url = reverse(
                "nucleos:detail_uuid",
                kwargs={"public_id": nucleo.public_id},
            )
        else:
            fallback_url = reverse("nucleos:list")
        back_href = resolve_back_href(
            self.request,
            fallback=fallback_url,
        )
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        return context

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type in {UserType.ADMIN, UserType.OPERADOR}:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    def get_success_url(self):
        if self.object:
            return reverse(
                "nucleos:detail_uuid",
                kwargs={"public_id": self.object.public_id},
            )
        return super().get_success_url()

    def form_valid(self, form):
        messages.success(self.request, _("Núcleo atualizado com sucesso."))
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            resp = HttpResponse(status=204)
            resp["HX-Redirect"] = str(self.get_success_url())
            return resp
        return response

class NucleoDeleteView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")

        is_htmx = bool(request.headers.get("HX-Request"))
        form_action = reverse("nucleos:delete", args=[nucleo.pk])

        if is_htmx:
            contexto_modal = {
                "objeto": nucleo,
                "titulo": _("Remover Núcleo"),
                "mensagem": format_html(
                    _("Tem certeza que deseja remover o núcleo <strong>{nome}</strong>?"),
                    nome=nucleo.nome,
                ),
                "submit_label": _("Remover"),
                "form_action": form_action,
            }
            return render(request, "nucleos/partials/nucleo_delete_modal.html", contexto_modal)

        back_href = self._resolve_back_href(request, nucleo)
        fallback_url = reverse("nucleos:detail", args=[nucleo.pk])
        return render(
            request,
            "nucleos/delete.html",
            {
                "object": nucleo,
                "back_href": back_href,
                "back_component_config": {
                    "href": back_href,
                    "fallback_href": fallback_url,
                    "variant": "compact",
                },
                "cancel_component_config": {
                    "href": back_href,
                    "fallback_href": fallback_url,
                    "aria_label": _("Cancelar remoção"),
                },
            },
        )

    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        nucleo.soft_delete()
        messages.success(request, _("Núcleo removido."))
        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("nucleos:list")
            return response
        return redirect("nucleos:list")

    def _resolve_back_href(self, request, nucleo: Nucleo) -> str:
        fallback = reverse("nucleos:detail", args=[nucleo.pk])
        return resolve_back_href(request, fallback=fallback)


class NucleoDetailView(NucleoPainelRenderMixin, NoSuperadminMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/partials/membros_list.html"
    partial_template_name = "nucleos/partials/membros_list.html"

    def get_membros_paginate_by(self) -> int:
        return getattr(settings, "NUCLEOS_MEMBROS_PAGINATE_BY", 12)

    def get_participacoes_queryset(self):
        nucleo = self.object
        return (
            nucleo.participacoes.filter(
                status="ativo",
                status_suspensao=False,
                user__user_type__in=[UserType.NUCLEADO.value, UserType.COORDENADOR.value],
                user__deleted=False,
            )
            .select_related("user")
            .order_by("-created_at")
        )

    def get_membros_queryset(self):
        qs = self.get_participacoes_queryset()
        papel_filter = self.request.GET.get("papel", "todos")
        if papel_filter not in {"todos", "membro", "coordenador"}:
            papel_filter = "todos"

        if papel_filter == "membro":
            qs = qs.exclude(papel="coordenador")
        elif papel_filter == "coordenador":
            qs = qs.filter(papel="coordenador")

        search_term = self.request.GET.get("search", "").strip()
        if search_term:
            # O modelo de usuário personalizado não possui os campos ``first_name``
            # e ``last_name`` herdados do ``AbstractUser``. Usamos os campos
            # disponíveis que compõem o nome exibido para o usuário.
            for term in search_term.split():
                qs = qs.filter(
                    Q(user__contato__icontains=term)
                    | Q(user__nome_fantasia__icontains=term)
                    | Q(user__email__icontains=term)
                    | Q(user__username__icontains=term)
                )

        self.papel_filter = papel_filter
        self.search_term = search_term
        return qs

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False).prefetch_related("participacoes__user", "coordenadores_suplentes")
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        public_id = self.kwargs.get("public_id")
        if public_id:
            return get_object_or_404(queryset, public_id=public_id)
        return super().get_object(queryset)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nucleo = self.object
        # Lista de membros ativos (nucleados) com paginação
        base_participacoes_qs = self.get_participacoes_queryset()
        ctx["total_membros"] = base_participacoes_qs.count()
        ctx["total_coordenadores"] = base_participacoes_qs.filter(papel="coordenador").count()

        membros_qs = self.get_membros_queryset()
        paginator = Paginator(membros_qs, self.get_membros_paginate_by())
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx["page_obj"] = page_obj
        ctx["membros_ativos"] = page_obj.object_list
        ctx["coordenadores"] = self.get_participacoes_queryset().filter(papel="coordenador")
        # Pendentes e suplentes (somente leitura)
        ctx["membros_pendentes"] = nucleo.participacoes.filter(status="pendente")
        ctx["suplentes"] = nucleo.coordenadores_suplentes.all()
        part = nucleo.participacoes.filter(user=self.request.user).first()
        ctx["mostrar_solicitar"] = (not part) or part.status == "inativo"
        if part and part.status == "ativo" and not part.status_suspensao:
            ctx["pode_postar"] = True

        pode_gerenciar_portfolio = _usuario_pode_gerenciar_portfolio_nucleo(
            self.request.user, nucleo
        )
        portfolio_filter_form = NucleoPortfolioFilterForm(self.request.GET or None)
        portfolio_query = ""
        if portfolio_filter_form.is_valid():
            portfolio_query = portfolio_filter_form.cleaned_data.get("q", "") or ""

        base_portfolio_qs = nucleo.midias.prefetch_related("tags").order_by("-created_at")
        all_portfolio_medias = list(base_portfolio_qs)
        portfolio_counts = _nucleo_portfolio_counts(all_portfolio_medias)

        if portfolio_query:
            portfolio_medias = list(
                base_portfolio_qs.filter(
                    Q(descricao__icontains=portfolio_query)
                    | Q(tags__nome__icontains=portfolio_query)
                ).distinct()
            )
        else:
            portfolio_medias = all_portfolio_medias

        portfolio_form = getattr(self, "_portfolio_form", None)
        portfolio_show_form = False
        if pode_gerenciar_portfolio:
            if portfolio_form is None:
                portfolio_form = NucleoMediaForm()
            _configure_nucleo_portfolio_form_fields(portfolio_form)
            portfolio_show_form = self.request.GET.get("portfolio_adicionar") == "1"
            if getattr(self, "_portfolio_show_form", False):
                portfolio_show_form = True
        else:
            portfolio_form = None

        portfolio_selected_media: NucleoMidia | None = None
        portfolio_show_detail = False
        portfolio_force_open = portfolio_show_form
        portfolio_media_id = self.request.GET.get("portfolio_midia")
        if portfolio_media_id:
            portfolio_selected_media = next(
                (
                    media
                    for media in all_portfolio_medias
                    if str(media.pk) == str(portfolio_media_id)
                ),
                None,
            )
            if portfolio_selected_media is not None:
                portfolio_show_detail = True
                portfolio_show_form = False
                portfolio_force_open = True

        params_without_detail = self.request.GET.copy()
        params_without_detail.pop("portfolio_midia", None)
        params_without_detail.pop("portfolio_adicionar", None)
        portfolio_query_base = params_without_detail.urlencode()
        portfolio_detail_back_url = self.request.path
        if portfolio_query_base:
            portfolio_detail_back_url = f"{self.request.path}?{portfolio_query_base}"

        ctx.update(
            {
                "pode_gerenciar_portfolio": pode_gerenciar_portfolio,
                "portfolio_medias": portfolio_medias,
                "portfolio_counts": portfolio_counts,
                "portfolio_filter_form": portfolio_filter_form,
                "portfolio_query": portfolio_query,
                "portfolio_form": portfolio_form,
                "portfolio_show_form": portfolio_show_form,
                "portfolio_selected_media": portfolio_selected_media,
                "portfolio_show_detail": portfolio_show_detail,
                "portfolio_force_open": portfolio_force_open,
                "portfolio_query_base": portfolio_query_base,
                "portfolio_detail_back_url": portfolio_detail_back_url,
            }
        )

        eventos_qs = Evento.objects.filter(nucleo=nucleo)
        ctx["eventos"] = eventos_qs.annotate(num_inscritos=Count("inscricoes", distinct=True))
        # Totais para cards
        # Totais de eventos por status
        ctx["total_eventos"] = eventos_qs.filter(
            status__in=[
                Evento.Status.PLANEJAMENTO,
                Evento.Status.ATIVO,
                Evento.Status.CONCLUIDO,
            ]
        ).count()
        ctx["total_eventos_planejamento"] = eventos_qs.filter(
            status=Evento.Status.PLANEJAMENTO
        ).count()
        ctx["total_eventos_ativos"] = eventos_qs.filter(
            status=Evento.Status.ATIVO
        ).count()
        ctx["total_eventos_concluidos"] = eventos_qs.filter(
            status=Evento.Status.CONCLUIDO
        ).count()

        section = self.request.GET.get("section", "membros")
        if section not in {"membros", "eventos", "feed"}:
            section = "membros"
        ctx["current_section"] = section

        ctx["current_papel_filter"] = getattr(self, "papel_filter", "todos")
        ctx["membros_search_query"] = getattr(self, "search_term", "")
        ctx["is_membros_filter_active"] = ctx["current_papel_filter"] in {"todos", "membro"}
        ctx["is_coordenadores_filter_active"] = ctx["current_papel_filter"] == "coordenador"

        card = self.request.GET.get("card", "membros")
        if card not in {"membros", "coordenadores"}:
            card = "membros"
        ctx["selected_card"] = card

        # Posts do feed do núcleo para a aba "Feed"
        try:
            from django.db.models import OuterRef, Subquery, Exists
            from feed.models import Post, Bookmark, Flag, Reacao, ModeracaoPost

            user = self.request.user
            latest_status = (
                ModeracaoPost.objects.filter(post=OuterRef("pk")).order_by("-created_at").values("status")[:1]
            )
            posts_qs = (
                Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
                .prefetch_related("reacoes", "comments", "tags", "bookmarks", "flags")
                .filter(deleted=False, tipo_feed="nucleo", nucleo=nucleo)
                .annotate(mod_status=Subquery(latest_status))
                .exclude(mod_status="rejeitado")
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
                    is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=user, deleted=False)),
                    is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=user, deleted=False)),
                    is_liked=Exists(Reacao.objects.filter(post=OuterRef("pk"), user=user, vote="like", deleted=False)),
                    is_shared=Exists(
                        Reacao.objects.filter(post=OuterRef("pk"), user=user, vote="share", deleted=False)
                    ),
                )
                .distinct()
            )
            if not user.is_staff:
                posts_qs = posts_qs.filter(Q(mod_status="aprovado") | Q(autor=user))
            ctx["nucleo_posts"] = posts_qs
        except Exception:
            # Se algo falhar nas anotações, degrade com lista simples
            try:
                from feed.models import Post

                ctx["nucleo_posts"] = (
                    Post.objects.filter(deleted=False, tipo_feed="nucleo", nucleo=nucleo)
                    .select_related("autor")
                    .order_by("-created_at")
                )
            except Exception:
                ctx["nucleo_posts"] = []

        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
        ctx["querystring"] = urlencode(params, doseq=True)
        ctx["membros_carousel_fetch_url"] = reverse("nucleos:membros_carousel_api", args=[nucleo.pk])

        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get("form_name") == "nucleo_portfolio":
            return self._handle_portfolio_post(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def _handle_portfolio_post(self, request, *args, **kwargs):
        if not _usuario_pode_gerenciar_portfolio_nucleo(request.user, self.object):
            raise PermissionDenied

        form = NucleoMediaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(nucleo=self.object)
            messages.success(request, _("Arquivo enviado com sucesso."))
            return redirect("nucleos:detail", pk=self.object.pk)

        self._portfolio_form = form
        self._portfolio_show_form = True
        return self.get(request, *args, **kwargs)


class NucleoMembrosPartialView(NucleoDetailView):
    template_name = "nucleos/partials/membros_list.html"


class NucleoMembrosCarouselView(NucleoMembrosPartialView):
    http_method_names = ["get"]

    def get_empty_message(self, card: str) -> str:
        if card == "coordenadores":
            return _("Sem coordenadores.")
        return _("Sem membros.")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        membros_qs = self.get_membros_queryset()
        paginator = Paginator(membros_qs, self.get_membros_paginate_by())
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        card = request.GET.get("card", "membros")
        if card not in {"membros", "coordenadores"}:
            card = "membros"

        html = render_to_string(
            "nucleos/partials/membros_carousel_slide.html",
            {
                "participacoes": page_obj.object_list,
                "page_number": page_obj.number,
                "empty_message": self.get_empty_message(card),
            },
            request=request,
        )

        return JsonResponse(
            {
                "html": html,
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "count": paginator.count,
            }
        )


class NucleoMetricsView(NoSuperadminMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/metrics.html"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nucleo = self.object
        ctx["nucleo"] = nucleo
        ctx["metrics_url"] = reverse("nucleos_api:nucleo-metrics", args=[nucleo.pk])
        return ctx


class NucleoMidiaBaseMixin(LoginRequiredMixin, NoSuperadminMixin):
    model = NucleoMidia

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not _usuario_pode_gerenciar_portfolio_nucleo(self.request.user, obj.nucleo):
            raise PermissionDenied
        return obj

    def get_success_url(self):
        return reverse("nucleos:detail", args=[self.object.nucleo.pk])


class NucleoPortfolioUpdateView(NucleoMidiaBaseMixin, UpdateView):
    form_class = NucleoMediaForm
    template_name = "nucleos/portfolio/form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        _configure_nucleo_portfolio_form_fields(form)
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Portfólio do núcleo atualizado."))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nucleo"] = self.object.nucleo
        context["title"] = _("Editar portfólio do núcleo")
        context["subtitle"] = self.object.descricao or ""
        context["back_href"] = reverse("nucleos:detail", args=[self.object.nucleo.pk])
        return context


class NucleoPortfolioDeleteView(NucleoMidiaBaseMixin, DeleteView):
    template_name = "nucleos/portfolio/confirm_delete.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.headers.get("HX-Target") == "modal":
            context = {
                "media": self.object,
                "titulo": _("Remover item do portfólio"),
                "mensagem": _("Tem certeza que deseja remover este item do portfólio do núcleo?"),
                "submit_label": _("Remover"),
                "form_action": reverse("nucleos:portfolio_delete", args=[self.object.pk]),
            }
            return TemplateResponse(request, "nucleos/portfolio/delete_modal.html", context)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_href"] = reverse("nucleos:detail", args=[self.object.nucleo.pk])
        context["nucleo"] = self.object.nucleo
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, _("Item do portfólio removido."))
        response = super().delete(request, *args, **kwargs)
        if bool(request.headers.get("HX-Request")):
            hx_response = HttpResponse(status=204)
            hx_response["HX-Redirect"] = self.get_success_url()
            return hx_response
        return response


class ParticipacaoCreateView(NoSuperadminMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao, created = ParticipacaoNucleo.all_objects.get_or_create(user=request.user, nucleo=nucleo)

        save_fields: list[str] = []
        if participacao.deleted:
            participacao.deleted = False
            participacao.deleted_at = None
            save_fields += ["deleted", "deleted_at"]

        if not created and participacao.status != "pendente":
            participacao.status = "pendente"
            participacao.data_solicitacao = timezone.now()
            participacao.decidido_por = None
            participacao.data_decisao = None
            participacao.justificativa = ""
            save_fields += [
                "status",
                "data_solicitacao",
                "decidido_por",
                "data_decisao",
                "justificativa",
            ]
            messages.success(request, _("Solicitação reenviada."))
        else:
            messages.success(request, _("Solicitação enviada."))

        if save_fields:
            participacao.save(update_fields=save_fields)
        return redirect("nucleos:detail", pk=pk)


class ParticipacaoDecisaoView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, FormView):
    form_class = ParticipacaoDecisaoForm

    def form_valid(self, form):
        nucleo = get_object_or_404(Nucleo, pk=self.kwargs["pk"])
        participacao = get_object_or_404(ParticipacaoNucleo, pk=self.kwargs["participacao_id"], nucleo=nucleo)
        if participacao.status != "pendente":
            return redirect("nucleos:detail", pk=nucleo.pk)
        participacao.decidido_por = self.request.user
        participacao.data_decisao = timezone.now()
        if form.cleaned_data["acao"] == "approve":
            participacao.status = "ativo"
            participacao.save(update_fields=["status", "decidido_por", "data_decisao"])
            notify_participacao_aprovada.delay(participacao.id)
            messages.success(self.request, _("Solicitação aprovada."))
        else:
            participacao.status = "inativo"
            participacao.save(update_fields=["status", "decidido_por", "data_decisao"])
            notify_participacao_recusada.delay(participacao.id)
            messages.success(self.request, _("Solicitação recusada."))
        return redirect("nucleos:detail", pk=nucleo.pk)


class MembroRemoveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        participacao.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse("")
        messages.success(request, _("Membro removido do núcleo."))
        return redirect("nucleos:detail", pk=pk)


class MembroPromoverView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        novo_papel = "membro" if participacao.papel == "coordenador" else "coordenador"
        participacao.papel = novo_papel
        participacao.save(update_fields=["papel"])
        if request.headers.get("HX-Request"):
            return render(
                request,
                "nucleos/partials/membro.html",
                {"part": participacao, "object": nucleo},
            )
        if novo_papel == "coordenador":
            messages.success(request, _("Membro promovido a coordenador."))
        else:
            messages.success(request, _("Cargo alterado para membro."))
        return redirect("nucleos:detail", pk=pk)


class SuplenteDeleteView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, suplente_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        suplente = get_object_or_404(CoordenadorSuplente, pk=suplente_id, nucleo=nucleo)
        suplente.delete()
        messages.success(request, _("Suplente removido."))
        return redirect("nucleos:detail", pk=pk)


class NucleoToggleActiveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo.all_objects, pk=pk)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        if nucleo.deleted:
            nucleo.undelete()
            messages.success(request, _("Núcleo ativado."))
        else:
            nucleo.soft_delete()
            messages.success(request, _("Núcleo desativado."))
        return redirect("nucleos:list")
