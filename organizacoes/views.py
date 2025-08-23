from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
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
from agenda.models import Evento
from core.cache import get_cache_version
from core.permissions import AdminRequiredMixin, SuperadminRequiredMixin
from empresas.models import Empresa
from feed.models import Post
from nucleos.models import Nucleo

from .forms import OrganizacaoForm

from .models import Organizacao, OrganizacaoChangeLog, OrganizacaoAtividadeLog
from .services import exportar_logs_csv, registrar_log, serialize_organizacao

from .tasks import organizacao_alterada

User = get_user_model()


class OrganizacaoListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """Listagem de organizações com resposta em cache."""

    model = Organizacao
    template_name = "organizacoes/list.html"
    paginate_by = 10
    cache_timeout = 60

    def _cache_key(self) -> str:
        params = self.request.GET
        version = get_cache_version("organizacoes_list")
        keys = [
            str(getattr(self.request.user, "pk", "")),
            params.get("search", ""),
            params.get("tipo", ""),
            params.get("cidade", ""),
            params.get("estado", ""),
            params.get("ordering", ""),
            params.get("page", ""),
            params.get("inativa", ""),
            "hx" if self.request.headers.get("HX-Request") else "full",
        ]
        return f"organizacoes_list_v{version}_" + "_".join(keys)

    def get_queryset(self):
        qs = super().get_queryset().select_related("created_by").prefetch_related("evento_set", "nucleos", "users")

        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(pk=user.organizacao_id)

        search = self.request.GET.get("search")
        tipo = self.request.GET.get("tipo")
        cidade = self.request.GET.get("cidade")
        estado = self.request.GET.get("estado")
        ordering = self.request.GET.get("ordering", "nome")
        inativa = self.request.GET.get("inativa")

        if inativa is not None and inativa != "":
            qs = qs.filter(inativa=inativa.lower() in ["1", "true", "t", "yes"])
        else:
            qs = qs.filter(inativa=False)

        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(slug__icontains=search))
        if tipo:
            qs = qs.filter(tipo=tipo)
        if cidade:
            qs = qs.filter(cidade=cidade)
        if estado:
            qs = qs.filter(estado=estado)

        allowed_order = {"nome", "tipo", "cidade", "estado", "created_at"}
        if ordering not in allowed_order:
            ordering = "nome"
        return qs.order_by(ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = Organizacao._meta.get_field("tipo").choices
        qs = Organizacao.objects.filter(inativa=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(pk=user.organizacao_id)
        context["cidades"] = qs.exclude(cidade="").values_list("cidade", flat=True).distinct().order_by("cidade")
        context["estados"] = qs.exclude(estado="").values_list("estado", flat=True).distinct().order_by("estado")
        context["inativa"] = self.request.GET.get("inativa", "")
        return context

    def render_to_response(self, context, **response_kwargs):
        key = self._cache_key()

        cached = cache.get(key)
        if cached is not None:
            cached["X-Cache"] = "HIT"
            return cached

        is_htmx = self.request.headers.get("HX-Request")

        if is_htmx:
            response = render(
                self.request,
                "organizacoes/partials/list_section.html",
                context,
                **response_kwargs,
            )
        else:
            response = super().render_to_response(context, **response_kwargs)

        if hasattr(response, "render"):
            response.render()
        cache.set(key, response, self.cache_timeout)

        response["X-Cache"] = "MISS"
        return response


class OrganizacaoCreateView(SuperadminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/create.html"
    success_url = reverse_lazy("organizacoes:list")

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


class OrganizacaoUpdateView(SuperadminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/update.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset().filter(inativa=False)

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
                "nucleos",
                "empresas",
                "posts",
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
        usuarios = User.objects.filter(organizacao=org)
        nucleos = Nucleo.objects.filter(organizacao=org, deleted=False)
        eventos = Evento.objects.filter(organizacao=org)
        empresas = Empresa.objects.filter(organizacao=org, deleted=False)
        posts = Post.objects.filter(organizacao=org, deleted=False)
        context.update(
            {
                "usuarios": usuarios,
                "nucleos": nucleos,
                "eventos": eventos,
                "empresas": empresas,
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
            "empresas",
            "posts",
        }:
            return render(
                self.request,
                f"organizacoes/partials/{section}_list.html",
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
    template_name = "organizacoes/history.html"

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

            if request.GET.get("export") == "csv":
                return exportar_logs_csv(org)


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


class OrganizacaoEmpresasModalView(OrganizacaoModalBaseView):
    model = Empresa
    template_name = "organizacoes/empresas_modal.html"
    context_object_name = "empresas"
    section = "empresas"
    api_url_name = "organizacoes_api:organizacao-empresas-list"
    filter_kwargs = {"deleted": False}


class OrganizacaoPostsModalView(OrganizacaoModalBaseView):
    model = Post
    template_name = "organizacoes/posts_modal.html"
    context_object_name = "posts"
    section = "posts"
    api_url_name = "organizacoes_api:organizacao-posts-list"
    filter_kwargs = {"deleted": False}
