from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
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

from accounts.models import UserType
from core.permissions import AdminRequiredMixin, SuperadminRequiredMixin

from .forms import OrganizacaoForm
from .models import Organizacao, OrganizacaoLog
from .services import registrar_log, serialize_organizacao
from .tasks import organizacao_alterada

User = get_user_model()


class OrganizacaoListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = Organizacao
    template_name = "organizacoes/list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().filter(deleted=False, inativa=False).prefetch_related("users")
        query = self.request.GET.get("q")
        tipo = self.request.GET.get("tipo")
        cidade = self.request.GET.get("cidade")
        estado = self.request.GET.get("estado")
        order = self.request.GET.get("order", "nome")

        if query:
            qs = qs.filter(Q(nome__icontains=query) | Q(slug__icontains=query))
        if tipo:
            qs = qs.filter(tipo=tipo)
        if cidade:
            qs = qs.filter(cidade__icontains=cidade)
        if estado:
            qs = qs.filter(estado__icontains=estado)

        allowed_order = {"nome", "tipo", "cidade", "estado", "created"}
        if order not in allowed_order:
            order = "nome"
        return qs.order_by(order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = Organizacao._meta.get_field("tipo").choices
        return context


class OrganizacaoCreateView(SuperadminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/create.html"
    success_url = reverse_lazy("organizacoes:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Organização criada com sucesso."))
        novo = serialize_organizacao(self.object)
        registrar_log(self.object, self.request.user, "criada", {}, novo)
        organizacao_alterada.send(sender=self.__class__, organizacao=self.object, acao="criada")
        return response


class OrganizacaoUpdateView(SuperadminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/update.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)

    def form_valid(self, form):
        antiga = serialize_organizacao(self.get_object())
        response = super().form_valid(form)
        nova = serialize_organizacao(self.object)
        dif_antiga = {k: v for k, v in antiga.items() if antiga[k] != nova[k]}
        dif_nova = {k: v for k, v in nova.items() if antiga[k] != nova[k]}
        registrar_log(
            self.object,
            self.request.user,
            "atualizada",
            dif_antiga,
            dif_nova,
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=self.object, acao="atualizada")
        messages.success(self.request, _("Organização atualizada com sucesso."))
        return response


class OrganizacaoDeleteView(SuperadminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Organizacao
    template_name = "organizacoes/delete.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        antiga = serialize_organizacao(self.object)
        self.object.deleted = True
        self.object.save()
        registrar_log(
            self.object,
            request.user,
            "removida",
            antiga,
            {"deleted": True},
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=self.object, acao="removida")
        messages.success(self.request, _("Organização removida."))
        return redirect(self.success_url)


class OrganizacaoDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    model = Organizacao
    template_name = "organizacoes/detail.html"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(deleted=False)
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
        context.update(
            {
                "usuarios": org.users.all(),
                "nucleos": org.nucleos.all(),
                "empresas": org.empresas.all(),
                "posts": org.posts.all(),
                "eventos": org.evento_set.all(),
            }
        )
        return context


class OrganizacaoToggleActiveView(SuperadminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        org = get_object_or_404(Organizacao, pk=pk, deleted=False)
        antiga = serialize_organizacao(org)
        if org.inativa:
            org.inativa = False
            org.inativada_em = None
            acao = "reativada"
            msg = _("Organização reativada com sucesso.")
        else:
            org.inativa = True
            org.inativada_em = timezone.now()
            acao = "inativada"
            msg = _("Organização inativada com sucesso.")
        org.save()
        nova = serialize_organizacao(org)
        dif_antiga = {k: v for k, v in antiga.items() if antiga[k] != nova[k]}
        dif_nova = {k: v for k, v in nova.items() if antiga[k] != nova[k]}
        registrar_log(org, request.user, acao, dif_antiga, dif_nova)
        organizacao_alterada.send(sender=self.__class__, organizacao=org, acao=acao)
        messages.success(request, msg)
        return redirect("organizacoes:detail", pk=org.pk)


class OrganizacaoLogListView(SuperadminRequiredMixin, LoginRequiredMixin, ListView):
    model = OrganizacaoLog
    template_name = "organizacoes/logs.html"
    paginate_by = 20

    def get_queryset(self):
        return (
            OrganizacaoLog.objects.filter(organizacao_id=self.kwargs["pk"])
            .select_related("usuario")
            .order_by("-created_at")
        )
