from __future__ import annotations

import logging

from collections import Counter
from typing import Iterable, Mapping

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
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

from .forms import NucleoForm, NucleoSearchForm, ParticipacaoDecisaoForm
from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from .tasks import notify_participacao_aprovada, notify_participacao_recusada

logger = logging.getLogger(__name__)

User = get_user_model()


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
) -> list[dict[str, object]]:
    grouped: dict[str, list[Nucleo]] = {
        config["key"]: [] for config in NUCLEO_SECTION_CONFIG
    }

    for nucleo in current_items:
        grouped.setdefault(nucleo.classificacao, []).append(nucleo)

    sections: list[dict[str, object]] = []
    for config in NUCLEO_SECTION_CONFIG:
        key = config["key"]
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


class NucleoListView(NoSuperadminMixin, LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/nucleo_list.html"
    paginate_by = 10

    def get_classificacao(self) -> str | None:
        if hasattr(self, "_classificacao"):
            return self._classificacao

        classificacao = self.request.GET.get("classificacao")
        valid_choices = {choice.value for choice in Nucleo.Classificacao}
        if classificacao not in valid_choices:
            classificacao = None

        self._classificacao = classificacao
        return classificacao

    def get_queryset(self):
        if hasattr(self, "_cached_queryset"):
            return self._cached_queryset

        user = self.request.user
        q = self.request.GET.get("q", "")
        classificacao = self.get_classificacao()
        version = get_cache_version("nucleos_list")
        cache_key = f"nucleos_list:v{version}:{user.id}:{q}:{classificacao or 'all'}"

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

        qs = base_qs.filter(deleted=False)

        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        elif user.user_type in {UserType.ASSOCIADO, UserType.NUCLEADO}:
            qs = qs.filter(organizacao=user.organizacao)

        if q:
            qs = qs.filter(nome__icontains=q)

        # Armazena um queryset com os mesmos filtros aplicados para ser usado na
        # contagem dos cartões de classificação. O ``distinct()`` garante que
        # núcleos não sejam contabilizados mais de uma vez quando há múltiplas
        # participações relacionadas ao mesmo usuário.
        self._qs_for_counts = qs.distinct()

        cached_ids = cache.get(cache_key)
        if cached_ids is not None:
            result = list(base_qs.filter(pk__in=cached_ids).order_by("nome"))
            self._cached_queryset = result
            return result

        if classificacao:
            qs = qs.filter(classificacao=classificacao)

        ids = list(qs.order_by("nome").distinct().values_list("pk", flat=True))
        cache.set(cache_key, ids, 300)

        result = list(base_qs.filter(pk__in=ids).order_by("nome"))
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
            counts = {choice.value: 0 for choice in Nucleo.Classificacao}
            for row in base_qs.values("classificacao").annotate(total=Count("id", distinct=True)):
                counts[row["classificacao"]] = row["total"]

            classificacao_labels = [
                (Nucleo.Classificacao.EM_FORMACAO.value, _("Formação")),
                (Nucleo.Classificacao.PLANEJAMENTO.value, _("Planejamento")),
                (Nucleo.Classificacao.CONSTITUIDO.value, _("Constituído")),
            ]

            for classificacao, label in classificacao_labels:
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
        classificacao_totals: dict[str, int] = {
            config["key"]: 0 for config in NUCLEO_SECTION_CONFIG
        }

        if hasattr(base_qs_for_totals, "values"):
            for row in base_qs_for_totals.values("classificacao").annotate(total=Count("id", distinct=True)):
                classificacao_totals[row["classificacao"]] = row["total"]

        ctx["classificacao_totals"] = classificacao_totals
        ctx["nucleo_sections"] = build_nucleo_sections(
            list(ctx.get("object_list", [])), classificacao_totals
        )

        return ctx


class NucleoMeusView(NoSuperadminMixin, LoginRequiredMixin, ListView):
    model = Nucleo
    # Reutiliza o template padrão de listagem de núcleos para evitar duplicação
    template_name = "nucleos/nucleo_list.html"
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type == UserType.ADMIN:
            return redirect("nucleos:list")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        q = self.request.GET.get("q", "")
        version = get_cache_version("nucleos_meus")
        cache_key = f"nucleos_meus:v{version}:{user.id}:{q}"
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

        if hasattr(self, "_cached_queryset"):
            return self._cached_queryset

        if cached_ids is not None:
            qs = base_qs.filter(pk__in=cached_ids).order_by("nome")
            result = list(qs)
            self._cached_queryset = result
            return result

        qs = base_qs.filter(
            deleted=False,
            participacoes__user=user,
            participacoes__status="ativo",
            participacoes__status_suspensao=False,
        )

        if q:
            qs = qs.filter(nome__icontains=q)

        ids = list(qs.order_by("nome").distinct().values_list("pk", flat=True))
        cache.set(cache_key, ids, 300)

        result = list(base_qs.filter(pk__in=ids).order_by("nome"))
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
        current_items = list(ctx.get("object_list", []))
        all_items = list(self.get_queryset())
        counts = Counter(nucleo.classificacao for nucleo in all_items)
        classificacao_totals = {
            config["key"]: counts.get(config["key"], 0)
            for config in NUCLEO_SECTION_CONFIG
        }
        ctx["classificacao_totals"] = classificacao_totals
        ctx["nucleo_sections"] = build_nucleo_sections(
            current_items, classificacao_totals
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
            "variant": "compact",
        }
        context["cancel_component_config"] = {
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nucleo = context.get("object") or getattr(self, "object", None)
        if nucleo:
            fallback_url = reverse("nucleos:detail", args=[nucleo.pk])
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
            "variant": "compact",
        }
        context["cancel_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar edição"),
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
            return reverse("nucleos:detail", args=[self.object.pk])
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
        return nucleo.participacoes.filter(
            status="ativo",
            status_suspensao=False,
            user__user_type__in=[UserType.NUCLEADO.value, UserType.COORDENADOR.value],
        ).select_related("user").order_by("-created_at")

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
        ctx["coordenadores"] = nucleo.participacoes.filter(status="ativo", papel="coordenador")
        # Pendentes e suplentes (somente leitura)
        ctx["membros_pendentes"] = nucleo.participacoes.filter(status="pendente")
        ctx["suplentes"] = nucleo.coordenadores_suplentes.all()
        part = nucleo.participacoes.filter(user=self.request.user).first()
        ctx["mostrar_solicitar"] = (not part) or part.status == "inativo"
        if part and part.status == "ativo" and not part.status_suspensao:
            ctx["pode_postar"] = True

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

        return ctx


class NucleoMembrosPartialView(NucleoDetailView):
    template_name = "nucleos/partials/membros_list.html"


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
