from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.permissions import (GerenteRequiredMixin, NoSuperadminMixin,
                              no_superadmin_required)

from .forms import EmpresaForm, EmpresaSearchForm, TagForm, TagSearchForm
from .models import Empresa, Tag


# ------------------------------------------------------------------
# LISTA
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def lista_empresas(request):
    if request.user.is_superuser:
        empresas = Empresa.objects.all()
    else:
        empresas = Empresa.objects.filter(usuario__organization=request.user.organization)

    form = EmpresaSearchForm(request.GET or None)
    if form.is_valid() and form.cleaned_data["empresa"]:
        empresas = empresas.filter(pk=form.cleaned_data["empresa"].pk)

    return render(
        request,
        "empresas/lista.html",
        {"empresas": empresas, "form": form},
    )


# ------------------------------------------------------------------
# CADASTRAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
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
@no_superadmin_required
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
@no_superadmin_required
def buscar_empresas(request):
    query = request.GET.get("q", "")
    if request.user.is_superuser:
        empresas = Empresa.objects.all()
    else:
        empresas = Empresa.objects.filter(usuario__organization=request.user.organization)
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


class TagListView(
    NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, ListView
):
    model = Tag
    template_name = "empresas/tags_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.GET.get("categoria")
        if categoria in {Tag.Categoria.PRODUTO, Tag.Categoria.SERVICO}:
            qs = qs.filter(categoria=categoria)
        form = TagSearchForm(self.request.GET)
        if form.is_valid() and form.cleaned_data["tag"]:
            qs = qs.filter(pk=form.cleaned_data["tag"].pk)
        self.form = form
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = getattr(self, "form", TagSearchForm())
        return context


class TagCreateView(
    NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, CreateView
):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item criado com sucesso.")
        return super().form_valid(form)


class TagUpdateView(
    NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, UpdateView
):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item atualizado com sucesso.")
        return super().form_valid(form)


class TagDeleteView(
    NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, DeleteView
):
    model = Tag
    template_name = "empresas/tag_confirm_delete.html"
    success_url = reverse_lazy("empresas:tags_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Item removido.")
        return super().delete(request, *args, **kwargs)


# ------------------------------------------------------------------
# DETALHAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def detalhes_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if (
        not request.user.is_superuser
        and empresa.usuario.organization != request.user.organization  # Corrigido para usar 'organization'
    ):
        return HttpResponseForbidden()
    prod_tags = empresa.tags.filter(categoria=Tag.Categoria.PRODUTO)
    serv_tags = empresa.tags.filter(categoria=Tag.Categoria.SERVICO)
    context = {
        "empresa": empresa,
        "empresa_tags": empresa.tags.all(),
        "prod_tags": prod_tags,
        "serv_tags": serv_tags,
    }
    return render(request, "empresas/detail.htm", context)
