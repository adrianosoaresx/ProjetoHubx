from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
    View,
)
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin
from django.shortcuts import get_object_or_404, redirect

from .models import Nucleo
from .forms import NucleoForm, NucleoSearchForm

User = get_user_model()


class NucleoListView(GerenteRequiredMixin, LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.tipo_id == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.tipo_id == User.Tipo.GERENTE:
            qs = qs.filter(membros=user)
        form = NucleoSearchForm(self.request.GET)
        if form.is_valid() and form.cleaned_data["nucleo"]:
            qs = qs.filter(pk=form.cleaned_data["nucleo"].pk)
        self.form = form
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = getattr(self, "form", NucleoSearchForm())
        return context


class NucleoCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/create.html"
    success_url = reverse_lazy("nucleos:list")

    def form_valid(self, form):
        if self.request.user.tipo_id == User.Tipo.ADMIN:
            form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, "Núcleo criado com sucesso.")
        return super().form_valid(form)


class NucleoUpdateView(GerenteRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/update.html"
    success_url = reverse_lazy("nucleos:list")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.tipo_id == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.tipo_id == User.Tipo.GERENTE:
            qs = qs.filter(membros=user)
        return qs

    def form_valid(self, form):
        messages.success(self.request, "Núcleo atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["membros"] = self.object.membros.all()
        return context


class NucleoDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Nucleo
    template_name = "nucleos/delete.html"
    success_url = reverse_lazy("nucleos:list")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.tipo_id == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        return qs

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Núcleo removido.")
        return super().delete(request, *args, **kwargs)


class NucleoDetailView(GerenteRequiredMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/detail.html"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.tipo_id == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.tipo_id == User.Tipo.GERENTE:
            qs = qs.filter(membros=user)
        return qs


class NucleoMemberRemoveView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, user_id):
        nucleo = get_object_or_404(Nucleo, pk=pk)
        if request.user.tipo_id == User.Tipo.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        if request.user.tipo_id == User.Tipo.GERENTE and request.user not in nucleo.membros.all():
            return redirect("nucleos:list")
        membro = get_object_or_404(User, pk=user_id)
        nucleo.membros.remove(membro)
        messages.success(request, "Membro removido do núcleo.")
        return redirect("nucleos:update", pk=pk)


