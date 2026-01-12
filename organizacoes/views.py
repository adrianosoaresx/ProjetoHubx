from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from sentry_sdk import capture_exception
from typing import Any

from accounts.models import UserType
from eventos.models import Evento
from core.cache import get_cache_version
from core.permissions import AdminRequiredMixin, OrgAdminRequiredMixin, SuperadminRequiredMixin
from core.utils import resolve_back_href
from feed.models import Post
from nucleos.models import Nucleo

from .forms import OrganizacaoForm
from .models import Organizacao, OrganizacaoAtividadeLog, OrganizacaoChangeLog
from .services import registrar_log, serialize_organizacao
from .tasks import organizacao_alterada

User = get_user_model()


class OrganizacaoListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """Listagem de organizações com resposta em cache."""

    model = Organizacao
    template_name = "organizacoes/list.html"
    paginate_by = 10
    cache_timeout = 60

    def _cache_key(self) -> str:
        version = get_cache_version("organizacoes_list")
        keys = [
            str(getattr(self.request.user, "pk", "")),
            self.request.GET.get("page", ""),
            "hx" if self.request.headers.get("HX-Request") else "full",
        ]
        return f"organizacoes_list_v{version}_" + "_".join(keys)

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("created_by")
            .annotate(
                users_count=Count("users", distinct=True),
                nucleos_count=Count("nucleos", distinct=True),
                events_count=Count("evento", distinct=True),
            )
        )

        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(pk=user.organizacao_id)

        return qs.filter(inativa=False).order_by("nome")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def render_to_response(self, context, **response_kwargs):
        key = self._cache_key()

        cached = cache.get(key)
        if cached is not None:
            response = HttpResponse(cached)
            response["X-Cache"] = "HIT"
            return response

        is_htmx = self.request.headers.get("HX-Request")

        if is_htmx:
            response = render(
                self.request,
                "_partials/organizacoes/list_section.html",
                context,
                **response_kwargs,
            )
        else:
            response = super().render_to_response(context, **response_kwargs)

        if hasattr(response, "render"):
            response.render()
        cache.set(key, response.content, self.cache_timeout)

        response["X-Cache"] = "MISS"
        return response


class OrganizacaoCreateView(SuperadminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/organizacao_form.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        fallback_url = reverse("organizacoes:list")
        back_href = resolve_back_href(self.request, fallback=fallback_url)
        form = context.get("form")
        instance = getattr(form, "instance", None)
        image_preview_urls = {
            "avatar": getattr(instance.avatar, "url", "") if instance and getattr(instance, "avatar", None) else "",
            "cover": getattr(instance.cover, "url", "") if instance and getattr(instance, "cover", None) else "",
            "icone_site": getattr(instance.icone_site, "url", "")
            if instance and getattr(instance, "icone_site", None)
            else "",
        }
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        context["cancel_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        context["image_fields"] = ["avatar", "cover", "icone_site"]
        context["image_preview_urls"] = image_preview_urls
        return context

    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, _("Organização criada com sucesso."))
            novo = serialize_organizacao(self.object)
            registrar_log(self.object, self.request.user, "created", {}, novo)
            organizacao_alterada.send(sender=self.__class__, organizacao=self.object, acao="created")
            return response
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

    def form_invalid(self, form):
        capture_exception(ValidationError(form.errors))
        return super().form_invalid(form)


class OrganizacaoUpdateView(OrgAdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/organizacao_form.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        fallback_url = reverse("organizacoes:list")
        back_href = resolve_back_href(self.request, fallback=fallback_url)
        form = context.get("form")
        instance = getattr(form, "instance", None)
        image_preview_urls = {
            "avatar": getattr(instance.avatar, "url", "") if instance and getattr(instance, "avatar", None) else "",
            "cover": getattr(instance.cover, "url", "") if instance and getattr(instance, "cover", None) else "",
            "icone_site": getattr(instance.icone_site, "url", "")
            if instance and getattr(instance, "icone_site", None)
            else "",
        }
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        context["cancel_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar edição"),
        }
        if self.object:
            context["organizacao_usuarios_total"] = self.object.users.count()
            context["organizacao_nucleos_total"] = self.object.nucleos.count()
            context["organizacao_eventos_total"] = self.object.evento_set.count()
        context["image_fields"] = ["avatar", "cover", "icone_site"]
        context["image_preview_urls"] = image_preview_urls
        return context

    def get_queryset(self):
        qs = super().get_queryset().filter(inativa=False)
        org_id = getattr(self.request.user, "organizacao_id", None)
        if org_id:
            qs = qs.filter(pk=org_id)
        return qs

    def form_valid(self, form):
        try:
            antiga = serialize_organizacao(self.get_object())
            response = super().form_valid(form)
            nova = serialize_organizacao(self.object)
            campos_alterados = [campo for campo in form.changed_data if antiga.get(campo) != nova.get(campo)]
            dif_antiga = {campo: antiga[campo] for campo in campos_alterados}
            dif_nova = {campo: nova[campo] for campo in campos_alterados}
            for campo in campos_alterados:
                OrganizacaoChangeLog.objects.create(
                    organizacao=self.object,
                    campo_alterado=campo,
                    valor_antigo=str(dif_antiga[campo]),
                    valor_novo=str(dif_nova[campo]),
                    alterado_por=self.request.user,
                )
            registrar_log(
                self.object,
                self.request.user,
                "updated",
                dif_antiga,
                dif_nova,
            )
            organizacao_alterada.send(sender=self.__class__, organizacao=self.object, acao="updated")
            messages.success(self.request, _("Organização atualizada com sucesso."))
            return response
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise

    def form_invalid(self, form):
        capture_exception(ValidationError(form.errors))
        return super().form_invalid(form)


class OrganizacaoDeleteView(SuperadminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Organizacao
    template_name = "organizacoes/delete.html"
    success_url = reverse_lazy("organizacoes:list")

    def _is_htmx(self, request) -> bool:
        return bool(request.headers.get("HX-Request") or getattr(request, "htmx", False))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self._is_htmx(request):
            context = {
                "organizacao": self.object,
                "titulo": _("Remover Organização"),
                "mensagem": format_html(
                    _("Tem certeza que deseja remover <strong>{nome}</strong>?"),
                    nome=self.object.nome,
                ),
                "submit_label": _("Remover"),
                "form_action": reverse("organizacoes:delete", args=[self.object.pk]),
            }
            return TemplateResponse(
                request,
                "organizacoes/partials/organizacao_delete_modal.html",
                context,
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        fallback_url = str(self.success_url)
        back_href = resolve_back_href(self.request, fallback=fallback_url)
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        context["cancel_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar exclusão"),
        }
        return context

    def get_queryset(self):
        return super().get_queryset().filter(inativa=False)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        antiga = serialize_organizacao(self.object)
        self.object.delete()
        registrar_log(
            self.object,
            request.user,
            "deleted",
            antiga,
            {"deleted": True, "deleted_at": self.object.deleted_at.isoformat()},
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=self.object, acao="deleted")
        messages.success(self.request, _("Organização removida."))
        if self._is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = str(self.get_success_url())
            return response
        return redirect(self.success_url)


class OrganizacaoDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    model = Organizacao
    template_name = "organizacoes/detail.html"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(inativa=False)
            .prefetch_related(
                "users",
                Prefetch("nucleos", queryset=Nucleo.objects.filter(deleted=False)),
                Prefetch("posts", queryset=Post.objects.filter(deleted=False)),
                "evento_set",
            )
        )
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(pk=getattr(user, "organizacao_id", None))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.object
        usuarios = org.users.all()
        nucleos = org.nucleos.all()
        eventos = org.evento_set.all()
        posts = org.posts.all()
        context.update(
            {
                "usuarios": usuarios,
                "nucleos": nucleos,
                "eventos": eventos,
                "posts": posts,
            }
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        section = self.request.GET.get("section")
        if self.request.headers.get("HX-Request") and section in {
            "usuarios",
            "nucleos",
            "eventos",
            "posts",
        }:
            return render(
                self.request,
                f"_partials/organizacoes/{section}_list.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)


class OrganizacaoToggleActiveView(SuperadminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            org = Organizacao.all_objects.get(pk=pk)
        except Organizacao.DoesNotExist as e:
            capture_exception(e)
            raise Http404
        try:
            antiga = serialize_organizacao(org)
            if org.inativa:
                org.inativa = False
                org.inativada_em = None
                acao = "reactivated"
                msg = _("Organização reativada com sucesso.")
            else:
                org.inativa = True
                org.inativada_em = timezone.now()
                acao = "inactivated"
                msg = _("Organização inativada com sucesso.")
            org.save(update_fields=["inativa", "inativada_em"])
            nova = serialize_organizacao(org)
            dif_antiga = {k: v for k, v in antiga.items() if antiga[k] != nova[k]}
            dif_nova = {k: v for k, v in nova.items() if antiga[k] != nova[k]}
            registrar_log(org, request.user, acao, dif_antiga, dif_nova)
            organizacao_alterada.send(sender=self.__class__, organizacao=org, acao=acao)
            messages.success(request, msg)
            if org.inativa or org.deleted:
                return redirect("organizacoes:list")
            return redirect("organizacoes:detail", pk=org.pk)
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise


class OrganizacaoHistoryView(LoginRequiredMixin, View):
    template_name = "organizacoes/organizacao_history.html"

    def get(self, request, pk, *args, **kwargs):
        try:
            org = get_object_or_404(Organizacao, pk=pk)
            user = request.user
            if not (
                user.is_superuser
                or getattr(user, "user_type", None) == UserType.ROOT.value
                or user.get_tipo_usuario == UserType.ROOT.value
            ):
                return HttpResponseForbidden()

            change_logs = OrganizacaoChangeLog.all_objects.filter(organizacao=org).order_by("-created_at")[:10]
            atividade_logs = OrganizacaoAtividadeLog.all_objects.filter(organizacao=org).order_by("-created_at")[:10]
            return render(
                request,
                self.template_name,
                {
                    "organizacao": org,
                    "change_logs": change_logs,
                    "atividade_logs": atividade_logs,
                },
            )
        except Exception as e:  # pragma: no cover - auditing
            capture_exception(e)
            raise


class OrganizacaoModalBaseView(AdminRequiredMixin, LoginRequiredMixin, View):
    model = None
    template_name = ""
    context_object_name = ""
    section = ""
    api_url_name = ""
    filter_kwargs: dict[str, Any] = {}

    def get(self, request, pk):
        org = get_object_or_404(Organizacao, pk=pk, inativa=False)
        queryset = self.model.objects.filter(organizacao=org, **self.filter_kwargs)
        return render(
            request,
            self.template_name,
            {
                "organizacao": org,
                self.context_object_name: queryset,
                "refresh_url": reverse("organizacoes:detail", args=[org.pk]) + f"?section={self.section}",
                "api_url": reverse(self.api_url_name, kwargs={"organizacao_pk": org.pk}),
            },
        )


class OrganizacaoUsuariosModalView(OrganizacaoModalBaseView):
    model = User
    template_name = "organizacoes/usuarios_modal.html"
    context_object_name = "usuarios"
    section = "usuarios"
    api_url_name = "organizacoes_api:organizacao-usuarios-list"


class OrganizacaoNucleosModalView(OrganizacaoModalBaseView):
    model = Nucleo
    template_name = "organizacoes/nucleos_modal.html"
    context_object_name = "nucleos"
    section = "nucleos"
    api_url_name = "organizacoes_api:organizacao-nucleos-list"
    filter_kwargs = {"deleted": False}


class OrganizacaoEventosModalView(OrganizacaoModalBaseView):
    model = Evento
    template_name = "organizacoes/eventos_modal.html"
    context_object_name = "eventos"
    section = "eventos"
    api_url_name = "organizacoes_api:organizacao-eventos-list"


class OrganizacaoPostsModalView(OrganizacaoModalBaseView):
    model = Post
    template_name = "organizacoes/posts_modal.html"
    context_object_name = "posts"
    section = "posts"
    api_url_name = "organizacoes_api:organizacao-posts-list"
    filter_kwargs = {"deleted": False}
