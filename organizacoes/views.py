from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Organizacao
from .forms import OrganizacaoForm


class OrganizacaoListView(LoginRequiredMixin, ListView):
    model = Organizacao
    template_name = "organizacoes/list.html"


class OrganizacaoCreateView(LoginRequiredMixin, CreateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/create.html"
    success_url = reverse_lazy("organizacoes:list")

    def form_valid(self, form):
        messages.success(self.request, "Organização criada com sucesso.")
        return super().form_valid(form)


class OrganizacaoUpdateView(LoginRequiredMixin, UpdateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/update.html"
    success_url = reverse_lazy("organizacoes:list")

    def form_valid(self, form):
        messages.success(self.request, "Organização atualizada com sucesso.")
        return super().form_valid(form)


class OrganizacaoDeleteView(LoginRequiredMixin, DeleteView):
    model = Organizacao
    template_name = "organizacoes/delete.html"
    success_url = reverse_lazy("organizacoes:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Organização removida.")
        return super().delete(request, *args, **kwargs)
