from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Nucleo
from .forms import NucleoForm


class NucleoListView(LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/list.html"


class NucleoCreateView(LoginRequiredMixin, CreateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/create.html"
    success_url = reverse_lazy("nucleos:list")

    def form_valid(self, form):
        messages.success(self.request, "Núcleo criado com sucesso.")
        return super().form_valid(form)


class NucleoUpdateView(LoginRequiredMixin, UpdateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/update.html"
    success_url = reverse_lazy("nucleos:list")

    def form_valid(self, form):
        messages.success(self.request, "Núcleo atualizado com sucesso.")
        return super().form_valid(form)


class NucleoDeleteView(LoginRequiredMixin, DeleteView):
    model = Nucleo
    template_name = "nucleos/delete.html"
    success_url = reverse_lazy("nucleos:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Núcleo removido.")
        return super().delete(request, *args, **kwargs)
