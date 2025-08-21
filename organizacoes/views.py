from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
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
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from sentry_sdk import capture_exception

from accounts.models import UserType
from agenda.models import Evento
from core.permissions import AdminRequiredMixin, SuperadminRequiredMixin
from empresas.models import Empresa
from feed.models import Post
from nucleos.models import Nucleo

from .forms import OrganizacaoForm
from .models import Organizacao, OrganizacaoChangeLog, OrganizacaoAtividadeLog
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
        params = self.request.GET
        keys = [
            str(getattr(self.request.user, "pk", "")),
            params.get("search", ""),
            params.get("tipo", ""),
            params.get("cidade", ""),
            params.get("estado", ""),
            params.get("ordering", ""),
            params.get("page", ""),
            params.get("inativa", ""),
        ]
        return "organizacoes_list_" + "_".join(keys)

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("created_by")
            .prefetch_related("evento_set", "nucleos", "users")
        )
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
        context["cidades"] = (
            Organizacao.objects.filter(inativa=False)
            .exclude(cidade="")
            .values_list("cidade", flat=True)
            .distinct()
            .order_by("cidade")
        )
        context["estados"] = (
            Organizacao.objects.filter(inativa=False)
            .exclude(estado="")
            .values_list("estado", flat=True)
            .distinct()
            .order_by("estado")
        )
        context["inativa"] = self.request.GET.get("inativa", "")
        return context

    def render_to_response(self, context, **response_kwargs):
        key = self._cache_key()
        cached = cache.get(key)
        if cached is not None:
            cached["X-Cache"] = "HIT"
            return cached
        response = super().render_to_response(context, **response_kwargs)
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
            organizacao_alterada.send(
                sender=self.__class__, organizacao=self.object, acao="created"
            )
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
            dif_antiga = {k: v for k, v in antiga.items() if antiga[k] != nova[k]}
            dif_nova = {k: v for k, v in nova.items() if antiga[k] != nova[k]}
            for campo in [
                "nome",
                "tipo",
                "slug",
                "cnpj",
                "contato_nome",
                "contato_email",
            ]:
                if campo in dif_antiga:
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
            organizacao_alterada.send(
                sender=self.__class__, organizacao=self.object, acao="updated"
            )
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
            organizacao_alterada.send(
                sender=self.__class__, organizacao=org, acao=acao
            )
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
                import csv
                from django.http import HttpResponse

                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = f'attachment; filename="organizacao_{org.pk}_logs.csv"'
                writer = csv.writer(response)
                writer.writerow(["tipo", "campo/acao", "valor_antigo", "valor_novo", "usuario", "data"])
                for log in OrganizacaoChangeLog.all_objects.filter(organizacao=org).order_by("-created_at"):
                    writer.writerow([
                        "change",
                        log.campo_alterado,
                        log.valor_antigo,
                        log.valor_novo,
                        getattr(log.alterado_por, "email", ""),
                        log.created_at.isoformat(),
                    ])
                for log in OrganizacaoAtividadeLog.all_objects.filter(organizacao=org).order_by("-created_at"):
                    writer.writerow([
                        "activity",
                        log.acao,
                        "",
                        "",
                        getattr(log.usuario, "email", ""),
                        log.created_at.isoformat(),
                    ])
                return response

            change_logs = (
                OrganizacaoChangeLog.all_objects.filter(organizacao=org)
                .order_by("-created_at")[:10]
            )
            atividade_logs = (
                OrganizacaoAtividadeLog.all_objects.filter(organizacao=org)
                .order_by("-created_at")[:10]
            )
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


class OrganizacaoUsuariosModalView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organizacao, pk=pk, inativa=False)
        usuarios = User.objects.filter(organizacao=org)
        return render(
            request,
            "organizacoes/usuarios_modal.html",
            {
                "organizacao": org,
                "usuarios": usuarios,
                "refresh_url": reverse("organizacoes:detail", args=[org.pk]) + "?section=usuarios",
                "api_url": reverse(
                    "organizacoes_api:organizacao-usuarios-list", kwargs={"organizacao_pk": org.pk}
                ),
            },
        )


class OrganizacaoNucleosModalView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organizacao, pk=pk, inativa=False)
        nucleos = Nucleo.objects.filter(organizacao=org, deleted=False)
        return render(
            request,
            "organizacoes/nucleos_modal.html",
            {
                "organizacao": org,
                "nucleos": nucleos,
                "refresh_url": reverse("organizacoes:detail", args=[org.pk]) + "?section=nucleos",
                "api_url": reverse(
                    "organizacoes_api:organizacao-nucleos-list", kwargs={"organizacao_pk": org.pk}
                ),
            },
        )


class OrganizacaoEventosModalView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organizacao, pk=pk, inativa=False)
        eventos = Evento.objects.filter(organizacao=org)
        return render(
            request,
            "organizacoes/eventos_modal.html",
            {
                "organizacao": org,
                "eventos": eventos,
                "refresh_url": reverse("organizacoes:detail", args=[org.pk]) + "?section=eventos",
                "api_url": reverse(
                    "organizacoes_api:organizacao-eventos-list", kwargs={"organizacao_pk": org.pk}
                ),
            },
        )


class OrganizacaoEmpresasModalView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organizacao, pk=pk, inativa=False)
        empresas = Empresa.objects.filter(organizacao=org, deleted=False)
        return render(
            request,
            "organizacoes/empresas_modal.html",
            {
                "organizacao": org,
                "empresas": empresas,
                "refresh_url": reverse("organizacoes:detail", args=[org.pk]) + "?section=empresas",
                "api_url": reverse(
                    "organizacoes_api:organizacao-empresas-list", kwargs={"organizacao_pk": org.pk}
                ),
            },
        )


class OrganizacaoPostsModalView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        org = get_object_or_404(Organizacao, pk=pk, inativa=False)
        posts = Post.objects.filter(organizacao=org, deleted=False)
        return render(
            request,
            "organizacoes/posts_modal.html",
            {
                "organizacao": org,
                "posts": posts,
                "refresh_url": reverse("organizacoes:detail", args=[org.pk]) + "?section=posts",
                "api_url": reverse(
                    "organizacoes_api:organizacao-posts-list", kwargs={"organizacao_pk": org.pk}
                ),
            },
        )
