
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from django.contrib import messages

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from core.permissions import SuperadminRequiredMixin

from .models import Empresa, Tag
from .forms import EmpresaForm, TagForm


# ------------------------------------------------------------------
# LISTA
# ------------------------------------------------------------------
@login_required
def lista_empresas(request):
    empresas = Empresa.objects.filter(usuario=request.user)
    return render(request, "empresas/lista.html", {"empresas": empresas})


# ------------------------------------------------------------------
# CADASTRAR
# ------------------------------------------------------------------
@login_required
def nova_empresa(request):
    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.save(commit=False)
            empresa.usuario = request.user
            empresa.save()
            form.save_m2m()
            messages.success(request, "Empresa cadastrada com sucesso.")
            return redirect("empresas:lista")
    else:
        form = EmpresaForm()

    return render(request, "empresas/nova.html", {"form": form})


# ------------------------------------------------------------------
# EDITAR
# ------------------------------------------------------------------
@login_required
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Empresa atualizada com sucesso.")
            return redirect("empresas:lista")
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, "empresas/nova.html", {"form": form, "empresa": empresa})


# ------------------------------------------------------------------
# BUSCAR
# ------------------------------------------------------------------
@login_required
def buscar_empresas(request):
    query = request.GET.get("q", "")
    empresas = Empresa.objects.filter(usuario=request.user)
    if query:
        palavras = [p.strip() for p in query.split() if p.strip()]
        q_objects = Q()
        for palavra in palavras:
            q_objects |= Q(tags__nome__icontains=palavra)
            q_objects |= Q(palavras_chave__icontains=palavra)
            q_objects |= Q(nome__icontains=palavra)
            q_objects |= Q(descricao__icontains=palavra)
        empresas = empresas.filter(q_objects)
    empresas = empresas.distinct()
    return render(request, "empresas/busca.html", {"empresas": empresas, "q": query})


class TagListView(SuperadminRequiredMixin, LoginRequiredMixin, ListView):
    model = Tag
    template_name = "empresas/tags_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.GET.get("categoria")
        if categoria in {Tag.Categoria.PRODUTO, Tag.Categoria.SERVICO}:
            qs = qs.filter(categoria=categoria)
        return qs


class TagCreateView(SuperadminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item criado com sucesso.")
        return super().form_valid(form)


class TagUpdateView(SuperadminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item atualizado com sucesso.")
        return super().form_valid(form)


class TagDeleteView(SuperadminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Tag
    template_name = "empresas/tag_confirm_delete.html"
    success_url = reverse_lazy("empresas:tags_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Item removido.")
        return super().delete(request, *args, **kwargs)
