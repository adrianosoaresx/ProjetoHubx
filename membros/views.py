from __future__ import annotations

import json
from collections import defaultdict
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, ListView, TemplateView, View
from django.template.loader import render_to_string

from accounts.models import UserType
from core.permissions import MembrosRequiredMixin, NoSuperadminMixin
from core.utils import resolve_back_href
from nucleos.models import Nucleo, ParticipacaoNucleo

from .forms import OrganizacaoUserCreateForm

User = get_user_model()

MEMBRO_PROMOVER_CAROUSEL_PAGE_SIZE = 6


class MembrosPermissionMixin(MembrosRequiredMixin, NoSuperadminMixin):
    """Combines permission checks for membros views."""

    raise_exception = True

    def test_func(self):
        return MembrosRequiredMixin.test_func(self) and NoSuperadminMixin.test_func(self)


class MembrosPromocaoPermissionMixin(MembrosPermissionMixin):
    """Restricts acesso às telas de promoção a admins e operadores."""

    allowed_roles = {UserType.ADMIN.value, UserType.OPERADOR.value}

    def test_func(self):
        if not super().test_func():
            return False
        tipo_usuario = getattr(self.request.user, "get_tipo_usuario", None)
        return tipo_usuario in self.allowed_roles


class OrganizacaoUserCreateView(NoSuperadminMixin, LoginRequiredMixin, FormView):
    template_name = "membros/usuario_form.html"
    form_class = OrganizacaoUserCreateForm
    success_url = reverse_lazy("membros:membros_lista")

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fallback_url = reverse("membros:membros_lista")
        back_href = resolve_back_href(self.request, fallback=fallback_url)
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        context["cancel_component_config"] = {
            "href": fallback_url,
            "fallback_href": fallback_url,
            "prevent_history": True,
        }
        return context

    def form_valid(self, form):
        organizacao = getattr(self.request.user, "organizacao", None)
        if organizacao is None:
            raise PermissionDenied

        try:
            new_user = form.save(organizacao=organizacao)
        except IntegrityError as exc:
            error_message = str(exc)
            if "accounts_user.cnpj" in error_message:
                form.add_error("cnpj", _("Este CNPJ já está em uso."))
            else:
                form.add_error(None, _("Não foi possível salvar o usuário. Tente novamente."))
            return self.form_invalid(form)

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

    def _get_post_redirect_target(self) -> str | None:
        candidate = self.request.POST.get("next")
        if not candidate:
            return None

        if not url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return None

        parsed = urlparse(candidate)
        path = parsed.path or ""
        if parsed.query:
            path = f"{path}?{parsed.query}"
        if parsed.fragment:
            path = f"{path}#{parsed.fragment}"

        return path or candidate

    def get_success_url(self):
        redirect_target = self._get_post_redirect_target()
        if redirect_target and redirect_target != self.request.path:
            return redirect_target
        return super().get_success_url()


class MembroListDataMixin:
    sections = ("sem_nucleo", "nucleados", "consultores", "coordenadores", "inativos")
    paginate_by = 6

    def get_paginate_by(self) -> int:
        try:
            per_page = int(self.request.GET.get("per_page", self.paginate_by))
        except (TypeError, ValueError):
            return self.paginate_by
        return per_page if per_page > 0 else self.paginate_by

    def get_search_term(self) -> str:
        return (self.request.GET.get("q") or "").strip()

    def get_consultor_filter(self) -> Q:
        return Q(user_type=UserType.CONSULTOR.value)

    def get_coordenador_filter(self) -> Q:
        return (
            Q(user_type=UserType.COORDENADOR.value)
            | Q(is_coordenador=True)
            | Q(
                participacoes__papel="coordenador",
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            )
        )

    def get_filtered_queryset(self):
        User = get_user_model()
        organizacao = getattr(self.request.user, "organizacao", None)
        queryset = (
            User.objects.filter(organizacao=organizacao)
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
            .annotate(_order=Lower("username"))
            .order_by("_order", "id")
        )

        search_term = self.get_search_term()
        if search_term:
            queryset = queryset.filter(
                Q(username__icontains=search_term) | Q(contato__icontains=search_term)
            )

        return queryset.distinct()

    def get_section_queryset(self, base_queryset, section: str):
        active_participacao = ParticipacaoNucleo.objects.filter(
            user=OuterRef("pk"),
            status="ativo",
            status_suspensao=False,
        )
        if section == "sem_nucleo":
            excluded_user_types = {UserType.ADMIN.value, UserType.OPERADOR.value}
            return (
                base_queryset.filter(is_associado=True, is_active=True)
                .exclude(user_type__in=excluded_user_types)
                .annotate(has_active_participacao=Exists(active_participacao))
                .filter(has_active_participacao=False)
            )
        if section == "nucleados":
            return (
                base_queryset.filter(is_associado=True, is_active=True)
                .annotate(has_active_participacao=Exists(active_participacao))
                .filter(has_active_participacao=True)
            )
        if section == "consultores":
            return base_queryset.filter(self.get_consultor_filter(), is_active=True)
        if section == "coordenadores":
            return base_queryset.filter(self.get_coordenador_filter(), is_active=True)
        if section == "inativos":
            return base_queryset.filter(is_active=False)
        raise ValueError(f"Unknown section '{section}'")

    def get_section_page(self, base_queryset, section: str, *, page_number=None):
        queryset = self.get_section_queryset(base_queryset, section)
        paginator = Paginator(queryset, self.get_paginate_by())
        number = page_number or self.request.GET.get(f"{section}_page") or 1
        page_obj = paginator.get_page(number)
        return page_obj, paginator

    def get_empty_message(self, section: str) -> str:
        messages = {
            "sem_nucleo": _("Nenhum membro sem núcleo encontrado."),
            "nucleados": _("Nenhum membro nucleado encontrado."),
            "consultores": _("Nenhum consultor encontrado."),
            "coordenadores": _("Nenhum coordenador encontrado."),
            "inativos": _("Nenhum usuário inativo encontrado."),
        }
        return messages.get(section, _("Nenhum usuário encontrado."))

    def get_totals(self) -> dict[str, int]:
        User = get_user_model()
        organizacao = getattr(self.request.user, "organizacao", None)
        if organizacao is None:
            return {
                "total_usuarios": 0,
                "total_membros": 0,
                "total_nucleados": 0,
                "total_consultores": 0,
                "total_coordenadores": 0,
                "total_inativos": 0,
            }

        base_queryset = User.objects.filter(organizacao=organizacao)
        active_participacao = ParticipacaoNucleo.objects.filter(
            user=OuterRef("pk"),
            status="ativo",
            status_suspensao=False,
        )

        excluded_user_types = {UserType.ADMIN.value, UserType.OPERADOR.value}

        total_membros = (
            base_queryset.filter(is_associado=True, is_active=True)
            .exclude(user_type__in=excluded_user_types)
            .annotate(has_active_participacao=Exists(active_participacao))
            .filter(has_active_participacao=False)
            .count()
        )
        total_nucleados = (
            base_queryset.filter(is_associado=True, is_active=True)
            .annotate(has_active_participacao=Exists(active_participacao))
            .filter(has_active_participacao=True)
            .count()
        )

        total_inativos = (
            base_queryset.filter(
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
            .filter(is_active=False)
            .distinct()
            .count()
        )

        return {
            "total_usuarios": base_queryset.count(),
            "total_membros": total_membros,
            "total_nucleados": total_nucleados,
            "total_consultores": User.objects.filter(organizacao=organizacao)
            .filter(self.get_consultor_filter(), is_active=True)
            .distinct()
            .count(),
            "total_coordenadores": User.objects.filter(organizacao=organizacao)
            .filter(self.get_coordenador_filter(), is_active=True)
            .distinct()
            .count(),
            "total_inativos": total_inativos,
        }


class MembroListView(
    MembrosPermissionMixin,
    LoginRequiredMixin,
    MembroListDataMixin,
    TemplateView,
):
    template_name = "membros/membro_list.html"

    def get_open_section(self) -> str:
        section = (self.request.GET.get("section") or "").strip()
        if section in self.sections:
            return section
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = self.get_filtered_queryset()

        section_pages: dict[str, dict[str, object]] = {}
        for section in self.sections:
            page_obj, paginator = self.get_section_page(base_queryset, section)
            section_pages[section] = {
                "page": page_obj,
                "count": paginator.count,
                "total_pages": paginator.num_pages,
            }

        context.update(
            {
                "search_term": self.get_search_term(),
                "membros_fetch_url": reverse("membros:membros_lista_api"),
                "membros_sem_nucleo_page": section_pages["sem_nucleo"]["page"],
                "membros_sem_nucleo_count": section_pages["sem_nucleo"]["count"],
                "membros_nucleados_page": section_pages["nucleados"]["page"],
                "membros_nucleados_count": section_pages["nucleados"]["count"],
                "membros_consultores_page": section_pages["consultores"]["page"],
                "membros_consultores_count": section_pages["consultores"]["count"],
                "membros_coordenadores_page": section_pages["coordenadores"]["page"],
                "membros_coordenadores_count": section_pages["coordenadores"]["count"],
                "membros_inativos_page": section_pages["inativos"]["page"],
                "membros_inativos_count": section_pages["inativos"]["count"],
                "membros_section_empty_messages": {
                    section: self.get_empty_message(section)
                    for section in self.sections
                },
                "open_section": self.get_open_section(),
            }
        )

        context.update(self.get_totals())
        return context


class MembroSectionListView(
    MembrosPermissionMixin,
    LoginRequiredMixin,
    MembroListDataMixin,
    View,
):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        section = request.GET.get("section")
        if section not in self.sections:
            return JsonResponse({"error": _("Seção inválida.")}, status=400)

        show_promote_button = (
            (request.GET.get("show_promote_button") or "").lower() in {"1", "true", "on", "yes"}
        )

        base_queryset = self.get_filtered_queryset()
        page_obj, paginator = self.get_section_page(
            base_queryset, section, page_number=request.GET.get("page")
        )

        html = render_to_string(
            "membros/_carousel_slide.html",
            {
                "usuarios": page_obj.object_list,
                "page_number": page_obj.number,
                "empty_message": self.get_empty_message(section),
                "section": section,
                "show_promote_button": show_promote_button,
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


class MembroPromoverListView(MembrosPromocaoPermissionMixin, LoginRequiredMixin, ListView):
    template_name = "membros/promover_list.html"
    context_object_name = "membros"
    paginate_by = MEMBRO_PROMOVER_CAROUSEL_PAGE_SIZE

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
        if filtro_tipo == "membros":
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

        current_filter = self.get_current_filter()

        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")

        valid_filters = {"membros", "nucleados", "consultores", "coordenadores"}

        def build_url(filter_value: str | None) -> str:
            query_params = params.copy()
            if filter_value in valid_filters:
                query_params["tipo"] = filter_value
            else:
                query_params.pop("tipo", None)
            query_string = query_params.urlencode()
            return f"{self.request.path}?{query_string}" if query_string else self.request.path

        context["current_filter"] = current_filter
        context["membros_filter_url"] = build_url("membros")
        context["nucleados_filter_url"] = build_url("nucleados")
        context["consultores_filter_url"] = build_url("consultores")
        context["coordenadores_filter_url"] = build_url("coordenadores")
        context["todos_filter_url"] = build_url(None)
        context["is_membros_filter_active"] = current_filter == "membros"
        context["is_nucleados_filter_active"] = current_filter == "nucleados"
        context["is_consultores_filter_active"] = current_filter == "consultores"
        context["is_coordenadores_filter_active"] = current_filter == "coordenadores"

        organizacao = getattr(self, "organizacao", None)
        User = get_user_model()
        if organizacao:
            context["total_usuarios"] = User.objects.filter(organizacao=organizacao).count()
            context["total_membros"] = User.objects.filter(
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
            context["total_membros"] = 0
            context["total_nucleados"] = 0
            context["total_consultores"] = 0
            context["total_coordenadores"] = 0

        context["has_search"] = bool(context["search_term"].strip())
        context["promover_empty_message"] = self.get_empty_message()
        context["promover_carousel_fetch_url"] = reverse(
            "membros:membros_promover_carousel"
        )
        return context

    def get_current_filter(self) -> str:
        valid_filters = {"membros", "nucleados", "consultores", "coordenadores"}
        current_filter = self.request.GET.get("tipo") or ""
        if current_filter not in valid_filters:
            return "todos"
        return current_filter

    def get_empty_message(self) -> str:
        if getattr(self, "search_term", "").strip():
            return _("Nenhum membro encontrado para a busca informada.")
        return _("Nenhum membro disponível para promoção no momento.")


class MembroPromoverCarouselView(MembrosPromocaoPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        list_view = MembroPromoverListView()
        list_view.request = request
        list_view.args = ()
        list_view.kwargs = {}

        queryset = list_view.get_queryset()
        paginator = Paginator(queryset, MEMBRO_PROMOVER_CAROUSEL_PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page") or 1)

        empty_message = list_view.get_empty_message()

        html = render_to_string(
            "membros/partials/promover_carousel_slide.html",
            {
                "usuarios": page_obj.object_list,
                "page_number": page_obj.number,
                "empty_message": empty_message,
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


class MembroPromoverFormView(MembrosPromocaoPermissionMixin, LoginRequiredMixin, TemplateView):
    template_name = "membros/promover_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.organizacao = getattr(request.user, "organizacao", None)
        if self.organizacao is None:
            raise PermissionDenied(_("É necessário pertencer a uma organização para promover membros."))
        self.membro = get_object_or_404(
            User,
            pk=kwargs.get("pk"),
            organizacao=self.organizacao,
        )
        self.origin_section = self._resolve_origin_section(request)
        return super().dispatch(request, *args, **kwargs)

    def _resolve_origin_section(self, request) -> str:
        section = (request.GET.get("section") or request.POST.get("section") or "").strip()
        if section in MembroListDataMixin.sections:
            return section
        return ""

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
                .exclude(user=self.membro)
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
                    user=self.membro,
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
                .exclude(consultor=self.membro)
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
                    user=self.membro,
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

        with transaction.atomic():
            nucleos_queryset = {
                nucleo.id: nucleo
                for nucleo in Nucleo.objects.filter(
                    organizacao=self.organizacao,
                    id__in=valid_action_ids,
                ).select_for_update()
            }

            participacoes_map = {
                participacao.nucleo_id: participacao
                for participacao in ParticipacaoNucleo.objects.select_for_update()
                .filter(user=self.membro, nucleo_id__in=valid_action_ids)
            }

            for nucleo_id in set(remover_consultor_ids) & valid_action_ids:
                nucleo = nucleos_queryset.get(nucleo_id)
                if nucleo and nucleo.consultor_id == self.membro.pk:
                    nucleo.consultor = None
                    nucleo.save(update_fields=["consultor"])

            if valid_consultor_ids:
                for nucleo_id in valid_consultor_ids:
                    nucleo = nucleos_queryset.get(nucleo_id)
                    if not nucleo:
                        continue
                    if nucleo.consultor_id != self.membro.pk:
                        nucleo.consultor = self.membro
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
                        user=self.membro,
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
            user=self.membro,
            status="ativo",
            status_suspensao=False,
        )
        has_coordenador = remaining_participacoes.filter(papel="coordenador").exists()
        has_participacao = remaining_participacoes.exists()
        has_consultor = Nucleo.objects.filter(
            organizacao=self.organizacao,
            consultor=self.membro,
        ).exists()

        updates: list[str] = []
        if self.membro.is_coordenador != has_coordenador:
            self.membro.is_coordenador = has_coordenador
            updates.append("is_coordenador")

        if not (has_participacao or has_coordenador or has_consultor):
            if self.membro.nucleo is not None:
                self.membro.nucleo = None
                updates.append("nucleo")

        allowed_types = {
            UserType.ASSOCIADO,
            UserType.NUCLEADO,
            UserType.CONSULTOR,
            UserType.COORDENADOR,
        }
        try:
            current_type = UserType(self.membro.user_type)
        except ValueError:
            current_type = None

        if current_type in allowed_types:
            if has_coordenador:
                target_type = UserType.COORDENADOR
            elif has_consultor:
                target_type = UserType.CONSULTOR
            elif has_participacao:
                target_type = UserType.NUCLEADO
            else:
                target_type = UserType.ASSOCIADO
            if current_type != target_type:
                self.membro.user_type = target_type.value
                updates.append("user_type")

        if updates:
            self.membro.save(update_fields=updates)

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
                user=self.membro,
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
                is_target = participacao.user_id == self.membro.pk
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
                    "is_current_consultor": nucleo.consultor_id == self.membro.pk,
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
            "membro": self.membro,
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
            "origin_section": getattr(self, "origin_section", ""),
        }
