from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy

from .models import Categoria, Topico, Resposta
from .forms import TopicoForm, RespostaForm


class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "forum/categoria_list.html"


class TopicoListView(LoginRequiredMixin, ListView):
    model = Topico
    template_name = "forum/topico_list.html"

    def get_queryset(self):
        self.categoria = get_object_or_404(Categoria, pk=self.kwargs["categoria_pk"])
        return Topico.objects.filter(categoria=self.categoria)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categoria"] = self.categoria
        return context


class TopicoDetailView(LoginRequiredMixin, DetailView):
    model = Topico
    template_name = "forum/topico_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = RespostaForm()
        return context


class TopicoCreateView(LoginRequiredMixin, CreateView):
    model = Topico
    form_class = TopicoForm
    template_name = "forum/topico_form.html"

    def form_valid(self, form):
        form.instance.autor = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("forum:topico_detail", kwargs={"pk": self.object.pk})


class RespostaCreateView(LoginRequiredMixin, CreateView):
    model = Resposta
    form_class = RespostaForm

    def form_valid(self, form):
        self.topico = get_object_or_404(Topico, pk=self.kwargs["topico_pk"])
        form.instance.topico = self.topico
        form.instance.autor = self.request.user
        self.object = form.save()
        return redirect("forum:topico_detail", pk=self.topico.pk)
