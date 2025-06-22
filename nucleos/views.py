from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin

from .models import Nucleo
from .forms import NucleoForm

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
        return qs


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
