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
from django.db.models import Count, Q, Prefetch
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
from .permissions import can_manage_feed
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


def _user_can_manage_nucleacao_requests(
    user, nucleo: Nucleo, consultor_ids: set[int] | None = None
) -> bool:
    consultor_ids = consultor_ids or set()
    tipo = getattr(user, "get_tipo_usuario", None)
    if isinstance(tipo, UserType):
        tipo = tipo.value

    if tipo == UserType.ADMIN.value:
        return getattr(user, "organizacao_id", None) == getattr(nucleo, "organizacao_id", None)

    if tipo == UserType.COORDENADOR.value:
        participacoes = getattr(nucleo, "participacoes", None)
        if participacoes is not None:
            return participacoes.filter(
                user=user,
                status="ativo",
                status_suspensao=False,
            ).exists()
        return False

    if tipo == UserType.CONSULTOR.value or consultor_ids:
        return nucleo.pk in consultor_ids

    return False


class NucleoVisibilityMixin:
    guest_forbidden_message = _("Núcleos não estão disponíveis para usuários convidados.")

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        user_type = getattr(request.user, "get_tipo_usuario", None) or getattr(request.user, "user_type", None)
        if isinstance(user_type, UserType):
            user_type = user_type.value

        if user_type == UserType.CONVIDADO.value:
            raise PermissionDenied(self.guest_forbidden_message)

        return super().dispatch(request, *args, **kwargs)

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


NUCLEO_SECTION_PAGE_SIZE = 6


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


NUCLEO_SECTION_CONFIG_MAP = {config["key"]: config for config in NUCLEO_SECTION_CONFIG}


def build_custom_nucleo_section(
    request,
    queryset: Iterable[Nucleo],
    *,
    key: str,
    title: str,
    icon: str,
    icon_classes: str,
    empty_message: str,
    aria_label: str,
    scope: str | None = None,
    per_page: int = NUCLEO_SECTION_PAGE_SIZE,
):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(f"{key}_page") or 1
    page_obj = paginator.get_page(page_number)

    return {
        "key": key,
        "title": title,
        "icon": icon,
        "icon_classes": icon_classes,
        "empty_message": empty_message,
        "aria_label": aria_label,
        "total": paginator.count,
        "page_obj": page_obj,
        "fetch_url": "",
        "search_term": "",
        "scope": scope,
    }


def build_nucleo_sections(
    request,
    base_queryset: Iterable[Nucleo],
    totals_by_classificacao: Mapping[str, int],
    allowed_keys: Iterable[str],
    *,
    fetch_url: str = "",
    search_term: str = "",
    selected_classificacao: str | None = None,
    scope: str | None = None,
    per_page: int = NUCLEO_SECTION_PAGE_SIZE,
) -> list[dict[str, object]]:
    allowed_set = set(allowed_keys)

    sections: list[dict[str, object]] = []
    for config in NUCLEO_SECTION_CONFIG:
        key = config["key"]
        if key not in allowed_set:
            continue

        queryset = getattr(base_queryset, "filter", None)
        if callable(queryset):
            section_qs = base_queryset.filter(classificacao=key).order_by("nome").distinct()
        else:
            section_qs = [
                nucleo
                for nucleo in base_queryset
                if getattr(nucleo, "classificacao", None) == key
            ]

        if selected_classificacao and selected_classificacao != key:
            if callable(getattr(section_qs, "none", None)):
                section_qs = section_qs.none()
            else:
                section_qs = []

        paginator = Paginator(section_qs, per_page)
        page_number = request.GET.get(f"{key}_page") or 1
        page_obj = paginator.get_page(page_number)

        total = totals_by_classificacao.get(key, paginator.count)

        section = {
            **config,
            "total": total,
            "page_obj": page_obj,
            "fetch_url": fetch_url,
            "search_term": search_term,
            "scope": scope,
        }
        sections.append(section)

    return sections


class NucleoPainelRenderMixin(NucleoVisibilityMixin):
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

    def can_view_nucleacao_solicitacoes(self) -> bool:
        tipo = getattr(self.request.user, "get_tipo_usuario", None)
        if isinstance(tipo, UserType):
            tipo = tipo.value
        return tipo in {UserType.ADMIN.value, UserType.COORDENADOR.value} or self.user_has_consultoria_access()

    def get_nucleacao_solicitacoes_queryset(self):
        if not self.can_view_nucleacao_solicitacoes():
            return ParticipacaoNucleo.objects.none()

        user = self.request.user
        tipo = getattr(user, "get_tipo_usuario", None)
        if isinstance(tipo, UserType):
            tipo = tipo.value

        consultor_ids = self.get_consultor_nucleo_ids()

        qs = (
            ParticipacaoNucleo.objects.filter(status="pendente")
            .exclude(user__user_type=UserType.ADMIN.value)
            .select_related("user", "nucleo")
            .order_by("data_solicitacao")
        )

        if tipo == UserType.ADMIN.value:
            return qs.filter(nucleo__organizacao=user.organizacao)

        if tipo == UserType.COORDENADOR.value:
            return qs.filter(nucleo__participacoes__user=user).distinct()

        if self.user_has_consultoria_access():
            if consultor_ids:
                return qs.filter(nucleo_id__in=consultor_ids)
            return ParticipacaoNucleo.objects.none()

        return ParticipacaoNucleo.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("list_title", _("Núcleos"))
        ctx.setdefault("list_aria_label", _("Lista de núcleos"))
        ctx.setdefault("empty_message", _("Nenhum núcleo encontrado."))
        ctx.setdefault("list_hero_template", "_components/hero_nucleo.html")
        ctx.setdefault("list_hero_action_template", "nucleos/hero_actions_nucleo.html")
        ctx.setdefault("list_card_template", "_components/card_nucleo.html")
        ctx.setdefault("item_context_name", "nucleo")
        form = NucleoSearchForm(self.request.GET or None)
        ctx["form"] = form
        show_totals = self.request.user.user_type in {UserType.ADMIN, UserType.OPERADOR}
        ctx["show_totals"] = show_totals

        show_nucleacao_solicitacoes = self.can_view_nucleacao_solicitacoes()
        ctx["show_nucleacao_solicitacoes"] = show_nucleacao_solicitacoes
        ctx["nucleacao_solicitacoes"] = []
        ctx["total_nucleacao_solicitacoes"] = 0
        if show_nucleacao_solicitacoes:
            solicitacoes = list(self.get_nucleacao_solicitacoes_queryset())
            ctx["nucleacao_solicitacoes"] = solicitacoes
            ctx["total_nucleacao_solicitacoes"] = len(solicitacoes)

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

        search_term = ""
        if form.is_bound and form.is_valid():
            search_term = form.cleaned_data.get("q", "").strip()
        ctx["nucleos_search_term"] = search_term
        ctx["nucleos_carousel_fetch_url"] = reverse("nucleos:nucleos_carousel_api")
        ctx["nucleos_carousel_scope"] = "list"

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
        base_qs_for_totals = getattr(self, "_qs_for_counts", Nucleo.objects.none())
        sections = build_nucleo_sections(
            self.request,
            base_qs_for_totals,
            classificacao_totals,
            allowed_keys,
            fetch_url=ctx["nucleos_carousel_fetch_url"],
            search_term=search_term,
            selected_classificacao=selected_classificacao,
            scope=ctx["nucleos_carousel_scope"],
        )

        user_tipo = getattr(self.request.user, "get_tipo_usuario", None)
        allowed_user_types = {
            UserType.NUCLEADO.value,
            UserType.COORDENADOR.value,
            UserType.CONSULTOR.value,
        }

        if user_tipo in allowed_user_types:
            my_nucleos = (
                base_qs_for_totals.filter(
                    (
                        Q(
                            participacoes__user=self.request.user,
                            participacoes__status="ativo",
                            participacoes__status_suspensao=False,
                        )
                        | Q(consultor=self.request.user)
                    ),
                    classificacao=Nucleo.Classificacao.CONSTITUIDO,
                    ativo=True,
                )
                .order_by("nome")
                .distinct()
            )

            meus_section = build_custom_nucleo_section(
                self.request,
                my_nucleos,
                key="meus_nucleos",
                title=_("Meus núcleos"),
                icon="user-round-check",
                icon_classes="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary-500)]/10 text-[var(--color-primary-600)] shadow-lg shadow-[var(--color-primary-500)]/15",
                empty_message=_("Você ainda não faz parte de nenhum núcleo ativo."),
                aria_label=_("Lista de núcleos do associado"),
                scope="meus",
            )

            org_nucleos = (
                Nucleo.objects.select_related("organizacao")
                .filter(
                    classificacao=Nucleo.Classificacao.CONSTITUIDO,
                    ativo=True,
                    deleted=False,
                )
                .order_by("nome")
                .distinct()
            )

            user_organizacao = getattr(self.request.user, "organizacao", None)
            if user_organizacao:
                org_nucleos = org_nucleos.filter(organizacao=user_organizacao)
            else:
                org_nucleos = org_nucleos.filter(pk__in=base_qs_for_totals.values("pk"))

            todos_section = build_custom_nucleo_section(
                self.request,
                org_nucleos,
                key="todos_nucleos",
                title=_("Todos os núcleos"),
                icon="layout-grid",
                icon_classes="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-info-500)]/10 text-[var(--color-info-600)] shadow-lg shadow-[var(--color-info-500)]/15",
                empty_message=_("Nenhum núcleo constituído e ativo encontrado."),
                aria_label=_("Lista de todos os núcleos constituídos e ativos"),
                scope="todos",
            )

            sections = [meus_section, todos_section]

        ctx["nucleo_sections"] = sections

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
            self._qs_for_counts = qs.distinct()
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

        self._qs_for_counts = qs.distinct()

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
        form = NucleoSearchForm(self.request.GET or None)
        ctx["form"] = form
        ctx.setdefault("show_nucleacao_solicitacoes", False)
        ctx.setdefault("nucleacao_solicitacoes", [])
        ctx.setdefault("total_nucleacao_solicitacoes", 0)
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
        search_term = ""
        if form.is_bound and form.is_valid():
            search_term = form.cleaned_data.get("q", "").strip()
        ctx["nucleos_search_term"] = search_term
        ctx["nucleos_carousel_fetch_url"] = reverse("nucleos:nucleos_carousel_api")
        ctx["nucleos_carousel_scope"] = "meus"
        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
        ctx["querystring"] = urlencode(params, doseq=True)
        allowed_keys = self.get_allowed_classificacao_keys()
        ctx["allowed_classificacao_keys"] = sorted(allowed_keys)
        selected_classificacao = self.request.GET.get("classificacao")
        if selected_classificacao not in allowed_keys:
            selected_classificacao = None
        ctx["selected_classificacao"] = selected_classificacao
        base_qs_for_totals = getattr(self, "_qs_for_counts", Nucleo.objects.none())
        classificacao_totals: dict[str, int] = {key: 0 for key in allowed_keys}
        if hasattr(base_qs_for_totals, "values"):
            for row in base_qs_for_totals.values("classificacao").annotate(total=Count("id", distinct=True)):
                key = row["classificacao"]
                if key in classificacao_totals:
                    classificacao_totals[key] = row["total"]
        ctx["classificacao_totals"] = classificacao_totals
        ctx["nucleo_sections"] = build_nucleo_sections(
            self.request,
            base_qs_for_totals,
            classificacao_totals,
            allowed_keys,
            fetch_url=ctx["nucleos_carousel_fetch_url"],
            search_term=search_term,
            selected_classificacao=selected_classificacao,
            scope=ctx["nucleos_carousel_scope"],
        )

        return ctx


class NucleoListCarouselView(NoSuperadminMixin, LoginRequiredMixin, NucleoVisibilityMixin, View):
    http_method_names = ["get"]

    def get_paginate_by(self) -> int:
        try:
            per_page = int(self.request.GET.get("per_page", NUCLEO_SECTION_PAGE_SIZE))
        except (TypeError, ValueError):
            return NUCLEO_SECTION_PAGE_SIZE
        return per_page if per_page > 0 else NUCLEO_SECTION_PAGE_SIZE

    def _get_view_for_scope(self, scope: str):
        if scope == "meus":
            return NucleoMeusView()
        return NucleoListView()

    def get(self, request, *args, **kwargs):
        scope = request.GET.get("scope", "list")
        section_key = request.GET.get("section")

        view = self._get_view_for_scope(scope)
        view.setup(request, *args, **kwargs)
        view.get_queryset()

        allowed_keys = view.get_allowed_classificacao_keys()
        if section_key not in allowed_keys:
            return JsonResponse({"error": _("Seção inválida.")}, status=400)

        config = NUCLEO_SECTION_CONFIG_MAP.get(section_key)
        if config is None:
            return JsonResponse({"error": _("Seção inválida.")}, status=400)

        base_queryset = getattr(view, "_qs_for_counts", Nucleo.objects.none())

        if hasattr(view, "get_classificacao"):
            selected_classificacao = view.get_classificacao()
        else:
            selected_classificacao = request.GET.get("classificacao")
            if selected_classificacao not in allowed_keys:
                selected_classificacao = None

        if hasattr(base_queryset, "filter"):
            queryset = (
                base_queryset.filter(classificacao=section_key)
                .order_by("nome")
                .distinct()
            )
            if selected_classificacao and selected_classificacao != section_key:
                queryset = queryset.none()
        else:
            queryset = [
                nucleo
                for nucleo in base_queryset
                if getattr(nucleo, "classificacao", None) == section_key
                and (
                    not selected_classificacao
                    or selected_classificacao == section_key
                )
            ]

        paginator = Paginator(queryset, self.get_paginate_by())
        page_number = request.GET.get("page") or 1
        page_obj = paginator.get_page(page_number)

        html = render_to_string(
            "nucleos/partials/nucleo_carousel_slide.html",
            {
                "nucleos": list(page_obj.object_list),
                "page_number": page_obj.number,
                "empty_message": config.get("empty_message"),
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


class NucleoCreateView(
    NoSuperadminMixin, AdminOperatorOrCoordinatorRequiredMixin, LoginRequiredMixin, CreateView
):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/nucleo_form.html"
    success_url = reverse_lazy("nucleos:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nucleo = context.get("object") or getattr(self, "object", None)
        if nucleo:
            fallback_url = reverse(
                "nucleos:detail",
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
                "nucleos:detail",
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



class NucleoUuidRedirectView(NoSuperadminMixin, LoginRequiredMixin, View):
    def get(self, request, public_id):
        return redirect(
            reverse("nucleos:detail", kwargs={"public_id": public_id}),
            permanent=True,
        )


class NucleoLegacyRedirectView(NoSuperadminMixin, LoginRequiredMixin, View):
    target_name: str | None = None

    def get_target_name(self) -> str:
        if not self.target_name:
            raise ValueError("target_name must be configured")
        return self.target_name

    def get_nucleo(self):
        return get_object_or_404(Nucleo, pk=self.kwargs["pk"], deleted=False)

    def get_redirect_url(self, **kwargs):
        nucleo = self.get_nucleo()
        target_kwargs = {k: v for k, v in self.kwargs.items() if k != "pk"}
        target_kwargs["public_id"] = nucleo.public_id
        return reverse(self.get_target_name(), kwargs=target_kwargs)

    def get(self, request, *args, **kwargs):
        return redirect(self.get_redirect_url(**kwargs), permanent=True)

    def post(self, request, *args, **kwargs):
        return redirect(self.get_redirect_url(**kwargs), permanent=True)


class NucleoPortfolioLegacyRedirectView(NoSuperadminMixin, LoginRequiredMixin, View):
    target_name: str | None = None

    def get_target_name(self) -> str:
        if not self.target_name:
            raise ValueError("target_name must be configured")
        return self.target_name

    def get_media(self):
        return get_object_or_404(NucleoMidia.objects.select_related("nucleo"), pk=self.kwargs["pk"], deleted=False)

    def get_redirect_url(self, **kwargs):
        media = self.get_media()
        return reverse(
            self.get_target_name(),
            kwargs={"public_id": media.nucleo.public_id, "pk": media.pk},
        )

    def get(self, request, *args, **kwargs):
        return redirect(self.get_redirect_url(**kwargs), permanent=True)

    def post(self, request, *args, **kwargs):
        return redirect(self.get_redirect_url(**kwargs), permanent=True)

class NucleoDeleteView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, public_id):
        nucleo = get_object_or_404(Nucleo, public_id=public_id, deleted=False)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")

        is_htmx = bool(request.headers.get("HX-Request"))
        form_action = reverse("nucleos:delete", kwargs={"public_id": nucleo.public_id})

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
        fallback_url = reverse("nucleos:detail", kwargs={"public_id": nucleo.public_id})
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

    def post(self, request, public_id):
        nucleo = get_object_or_404(Nucleo, public_id=public_id, deleted=False)
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
        fallback = reverse("nucleos:detail", kwargs={"public_id": nucleo.public_id})
        return resolve_back_href(request, fallback=fallback)


class NucleoDetailView(NucleoPainelRenderMixin, NoSuperadminMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/partials/membros_list.html"
    partial_template_name = "nucleos/partials/membros_list.html"

    def get_membros_paginate_by(self) -> int:
        return getattr(settings, "NUCLEOS_MEMBROS_PAGINATE_BY", 12)

    def get_card_param(self) -> str:
        card = self.request.GET.get("card")
        papel = self.request.GET.get("papel")

        if not card and papel == "coordenador":
            return "coordenadores"

        if card in {"membros", "coordenadores"}:
            return card

        return "membros"

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
            .prefetch_related(
                Prefetch("user__participacoes", queryset=ParticipacaoNucleo.objects.select_related("nucleo")),
                "user__nucleos_consultoria",
            )
            .order_by("-created_at")
        )

    def get_membros_queryset(self):
        qs = self.get_participacoes_queryset()
        card = self.get_card_param()

        default_papel = "coordenador" if card == "coordenadores" else "membro"
        papel_filter = self.request.GET.get("papel", default_papel)
        if papel_filter not in {"todos", "membro", "coordenador"}:
            papel_filter = default_papel

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
            qs = qs.filter(organizacao=user.organizacao)
        return qs

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        public_id = self.kwargs.get("public_id")
        if not public_id:
            raise PermissionDenied(_("A URL pública do núcleo deve usar UUID."))
        return get_object_or_404(queryset, public_id=public_id)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nucleo = self.object
        # Lista de membros ativos (nucleados) com paginação
        base_participacoes_qs = self.get_participacoes_queryset()
        ctx["total_membros"] = base_participacoes_qs.exclude(papel="coordenador").count()
        ctx["total_coordenadores"] = base_participacoes_qs.filter(papel="coordenador").count()

        membros_qs = self.get_membros_queryset()
        paginator = Paginator(membros_qs, self.get_membros_paginate_by())
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx["page_obj"] = page_obj
        ctx["membros_ativos"] = page_obj.object_list
        coordenadores_qs = self.get_participacoes_queryset().filter(papel="coordenador")
        search_term = getattr(self, "search_term", "").strip()
        if search_term:
            for term in search_term.split():
                coordenadores_qs = coordenadores_qs.filter(
                    Q(user__contato__icontains=term)
                    | Q(user__nome_fantasia__icontains=term)
                    | Q(user__email__icontains=term)
                    | Q(user__username__icontains=term)
                )
        coordenadores_paginator = Paginator(coordenadores_qs, self.get_membros_paginate_by())
        coordenadores_page_number = page_number if self.get_card_param() == "coordenadores" else 1
        ctx["coordenadores_page_obj"] = coordenadores_paginator.get_page(coordenadores_page_number)
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

        card = self.get_card_param()
        ctx["card"] = card
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

        ctx["mostrar_feed_nucleo"] = can_manage_feed(self.request.user, nucleo)
        if ctx["mostrar_feed_nucleo"]:
            ctx["nucleo_feed_url"] = f"{reverse('feed:listar')}?tipo_feed=nucleo&nucleo={nucleo.pk}"

        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
        ctx["querystring"] = urlencode(params, doseq=True)
        ctx["membros_carousel_fetch_url"] = reverse("nucleos:membros_carousel_api", kwargs={"public_id": nucleo.public_id})

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
            return redirect("nucleos:detail", public_id=self.object.public_id)

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

        card = self.get_card_param()

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


class NucleoMetricsView(NucleoVisibilityMixin, NoSuperadminMixin, LoginRequiredMixin, DetailView):
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


class NucleoMidiaBaseMixin(LoginRequiredMixin, NoSuperadminMixin, NucleoVisibilityMixin):
    model = NucleoMidia

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        url_public_id = self.kwargs.get("public_id")
        if url_public_id and str(obj.nucleo.public_id) != str(url_public_id):
            raise PermissionDenied
        if not _usuario_pode_gerenciar_portfolio_nucleo(self.request.user, obj.nucleo):
            raise PermissionDenied
        return obj

    def get_success_url(self):
        return reverse("nucleos:detail", kwargs={"public_id": self.object.nucleo.public_id})


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
        context["back_href"] = reverse("nucleos:detail", kwargs={"public_id": self.object.nucleo.public_id})
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
                "form_action": reverse("nucleos:portfolio_delete", kwargs={"public_id": self.object.nucleo.public_id, "pk": self.object.pk}),
            }
            return TemplateResponse(request, "nucleos/portfolio/delete_modal.html", context)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_href"] = reverse("nucleos:detail", kwargs={"public_id": self.object.nucleo.public_id})
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


class NucleacaoInviteView(NoSuperadminMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/partials/nucleacao_invite.html"
    context_object_name = "nucleo"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user

        user_type = getattr(user, "get_tipo_usuario", None) or getattr(user, "user_type", None)
        if isinstance(user_type, UserType):
            user_type = user_type.value

        if user_type == UserType.ADMIN.value:
            qs = qs.filter(organizacao=user.organizacao)
        elif user_type == UserType.COORDENADOR.value:
            qs = qs.filter(organizacao=user.organizacao)
        allowed_keys = _get_allowed_classificacao_keys(user)
        return qs.filter(classificacao__in=allowed_keys)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["participar_url"] = reverse("nucleos:participacao_solicitar", kwargs={"public_id": self.object.public_id})
        return context


class NucleoCardCtaPartialView(NoSuperadminMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/partials/nucleo_card_cta.html"
    context_object_name = "nucleo"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user

        user_type = getattr(user, "get_tipo_usuario", None) or getattr(user, "user_type", None)
        if isinstance(user_type, UserType):
            user_type = user_type.value

        if user_type in {UserType.ADMIN.value, UserType.COORDENADOR.value}:
            qs = qs.filter(organizacao=user.organizacao)

        allowed_keys = _get_allowed_classificacao_keys(user)
        return qs.filter(classificacao__in=allowed_keys)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resolved_nucleo"] = self.object
        context["cta_url"] = reverse("nucleos:nucleacao_invite", kwargs={"public_id": self.object.public_id})
        context["cta_label"] = _("Quero me nuclear")
        context["cta_hx_get"] = context["cta_url"]
        context["cta_hx_target"] = "#modal"
        context["cta_hx_swap"] = "innerHTML"
        context["cta_hx_on"] = (
            "htmx:beforeRequest: "
            "window.HubxModalTrigger = this; "
            f"window.HubxModalTriggerContainer = 'nucleo-cta-{self.object.public_id}';"
        )
        context["cta_container_id"] = f"nucleo-cta-{self.object.public_id}"
        context["cta_focus_id"] = f"nucleo-cta-focus-{self.object.public_id}"
        context["cta_container_classes"] = ""
        context["cta_classes"] = "btn btn-primary btn-sm relative z-20"
        return context


class NucleacaoPromoverSolicitacaoView(
    NoSuperadminMixin, LoginRequiredMixin, NucleoVisibilityMixin, View
):
    template_name = "nucleos/partials/nucleacao_promover_modal.html"

    def get_participacao(self):
        return get_object_or_404(
            ParticipacaoNucleo, pk=self.kwargs["participacao_id"], status="pendente"
        )

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        participacao = self.get_participacao()
        consultor_ids = self.get_consultor_nucleo_ids()
        if not _user_can_manage_nucleacao_requests(
            request.user, participacao.nucleo, consultor_ids
        ):
            raise PermissionDenied
        self.participacao = participacao
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = {
            "participacao": self.participacao,
            "form_action": reverse(
                "nucleos:nucleacao_promover", args=[self.participacao.pk]
            ),
        }
        return TemplateResponse(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        participacao: ParticipacaoNucleo = self.participacao
        if participacao.status != "pendente":
            return redirect("nucleos:list")

        participacao.status = "ativo"
        participacao.decidido_por = request.user
        participacao.data_decisao = timezone.now()
        participacao.justificativa = ""
        participacao.save(
            update_fields=[
                "status",
                "decidido_por",
                "data_decisao",
                "justificativa",
            ]
        )
        notify_participacao_aprovada.delay(participacao.id)
        messages.success(
            request,
            _("Solicitação aprovada e usuário promovido a nucleado."),
        )

        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Refresh"] = "true"
            return response

        return redirect("nucleos:list")


class NucleacaoCancelarSolicitacaoView(
    NoSuperadminMixin, LoginRequiredMixin, NucleoVisibilityMixin, View
):
    def get_participacao(self):
        return get_object_or_404(
            ParticipacaoNucleo, pk=self.kwargs["participacao_id"], status="pendente"
        )

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        participacao = self.get_participacao()
        consultor_ids = self.get_consultor_nucleo_ids()
        if not _user_can_manage_nucleacao_requests(
            request.user, participacao.nucleo, consultor_ids
        ):
            raise PermissionDenied
        self.participacao = participacao
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        participacao: ParticipacaoNucleo = self.participacao
        if participacao.status != "pendente":
            return redirect("nucleos:list")

        participacao.status = "inativo"
        participacao.decidido_por = request.user
        participacao.data_decisao = timezone.now()
        participacao.save(update_fields=["status", "decidido_por", "data_decisao"])

        messages.success(request, _("Solicitação de nucleação cancelada."))

        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Refresh"] = "true"
            return response

        return redirect("nucleos:list")


class ParticipacaoCreateView(NoSuperadminMixin, LoginRequiredMixin, View):
    @staticmethod
    def _build_cta_context(*, nucleo: Nucleo, status: str) -> dict[str, str]:
        context = {
            "nucleo": nucleo,
            "resolved_nucleo": nucleo,
            "nucleo_public_id": str(nucleo.public_id),
            "nucleacao_status": status,
            "cta_url": reverse("nucleos:nucleacao_invite", kwargs={"public_id": nucleo.public_id}),
            "cta_label": _("Quero me nuclear"),
            "cta_hx_target": "#modal",
            "cta_hx_swap": "innerHTML",
            "cta_hx_on": (
                "htmx:beforeRequest: "
                "window.HubxModalTrigger = this; "
                f"window.HubxModalTriggerContainer = 'nucleo-cta-{nucleo.public_id}';"
            ),
            "cta_container_id": f"nucleo-cta-{nucleo.public_id}",
            "cta_focus_id": f"nucleo-cta-focus-{nucleo.public_id}",
            "cta_classes": "btn btn-primary btn-sm relative z-20",
        }
        context["cta_hx_get"] = context["cta_url"]
        return context

    def post(self, request, public_id):
        nucleo = get_object_or_404(Nucleo, public_id=public_id, deleted=False)
        user = request.user
        user_type = getattr(user, "get_tipo_usuario", None) or getattr(user, "user_type", None)
        if isinstance(user_type, UserType):
            user_type = user_type.value

        if user_type == UserType.ADMIN.value:
            messages.error(request, _("Administradores não podem solicitar nucleação."))
            return redirect("nucleos:detail", public_id=nucleo.public_id)

        if user_type not in {
            UserType.ASSOCIADO.value,
            UserType.NUCLEADO.value,
            UserType.COORDENADOR.value,
        }:
            messages.error(request, _("Seu perfil não pode solicitar nucleação."))
            return redirect("nucleos:detail", public_id=nucleo.public_id)

        if getattr(user, "organizacao_id", None) != getattr(nucleo, "organizacao_id", None):
            messages.error(request, _("Você só pode solicitar nucleação em núcleos da sua organização."))
            return redirect("nucleos:detail", public_id=nucleo.public_id)

        participacao, created = ParticipacaoNucleo.all_objects.get_or_create(user=user, nucleo=nucleo)

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
        if bool(request.headers.get("HX-Request")):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "nucleacao:close-modal"
            response["HX-Refresh"] = "true"
            return response
        return redirect("nucleos:detail", public_id=nucleo.public_id)


class ParticipacaoDecisaoView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, FormView):
    form_class = ParticipacaoDecisaoForm

    def form_valid(self, form):
        nucleo = get_object_or_404(Nucleo, public_id=self.kwargs["public_id"])
        participacao = get_object_or_404(ParticipacaoNucleo, pk=self.kwargs["participacao_id"], nucleo=nucleo)
        if participacao.status != "pendente":
            return redirect("nucleos:detail", public_id=nucleo.public_id)
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
        return redirect("nucleos:detail", public_id=nucleo.public_id)


class MembroRemoveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, public_id, participacao_id):
        nucleo = get_object_or_404(Nucleo, public_id=public_id, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        participacao.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse("")
        messages.success(request, _("Membro removido do núcleo."))
        return redirect("nucleos:detail", public_id=nucleo.public_id)


class MembroPromoverView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, public_id, participacao_id):
        nucleo = get_object_or_404(Nucleo, public_id=public_id, deleted=False)
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
        return redirect("nucleos:detail", public_id=nucleo.public_id)


class SuplenteDeleteView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, public_id, suplente_id):
        nucleo = get_object_or_404(Nucleo, public_id=public_id, deleted=False)
        suplente = get_object_or_404(CoordenadorSuplente, pk=suplente_id, nucleo=nucleo)
        suplente.delete()
        messages.success(request, _("Suplente removido."))
        return redirect("nucleos:detail", public_id=nucleo.public_id)


class NucleoToggleActiveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, public_id):
        nucleo = get_object_or_404(Nucleo.all_objects, public_id=public_id)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        if nucleo.deleted:
            nucleo.undelete()
            messages.success(request, _("Núcleo ativado."))
        else:
            nucleo.soft_delete()
            messages.success(request, _("Núcleo desativado."))
        return redirect("nucleos:list")
