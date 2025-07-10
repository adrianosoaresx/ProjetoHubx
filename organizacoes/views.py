from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from core.permissions import SuperadminRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Organizacao
from .forms import OrganizacaoForm

User = get_user_model()


class OrganizacaoListView(SuperadminRequiredMixin, LoginRequiredMixin, ListView):
    model = Organizacao
    template_name = "organizacoes/list.html"

    def get_queryset(self):
        return super().get_queryset()


class OrganizacaoCreateView(SuperadminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/create.html"
    success_url = reverse_lazy("organizacoes:list")

    def form_valid(self, form):
        messages.success(self.request, "Organização criada com sucesso.")
        return super().form_valid(form)


class OrganizacaoUpdateView(SuperadminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/update.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Organização atualizada com sucesso.")
        return super().form_valid(form)


class OrganizacaoDeleteView(SuperadminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Organizacao
    template_name = "organizacoes/delete.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset()

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Organização removida.")
        return super().delete(request, *args, **kwargs)
