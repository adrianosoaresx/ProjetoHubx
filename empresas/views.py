from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from accounts.models import UserType
from core.permissions import ClienteGerenteRequiredMixin, NoSuperadminMixin, no_superadmin_required, pode_crud_empresa

from .forms import (
    ContatoEmpresaForm,
    EmpresaForm,
    TagForm,
    TagSearchForm,
)
from .models import ContatoEmpresa, Empresa, Tag


# ------------------------------------------------------------------
# LISTA
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def lista_empresas(request):
    qs = Empresa.objects.select_related("organizacao", "usuario").prefetch_related("contatos")
    if request.user.is_superuser:
        empresas = qs
    elif request.user.user_type == UserType.ADMIN:
        empresas = qs.filter(organizacao=request.user.organizacao)
    elif request.user.user_type in [UserType.NUCLEADO, UserType.COORDENADOR]:
        empresas = qs.filter(usuario=request.user)
    else:
        return HttpResponseForbidden("Usuário não autorizado.")

    nome = request.GET.get("nome", "")
    segmento = request.GET.get("segmento", "")
    if nome:
        empresas = empresas.filter(nome__icontains=nome)
    if segmento:
        empresas = empresas.filter(tipo__icontains=segmento)

    paginator = Paginator(empresas, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "empresas": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }

    template = "empresas/includes/empresas_table.html" if request.headers.get("HX-Request") else "empresas/lista.html"

    return render(request, template, context)


# ------------------------------------------------------------------
# CADASTRAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def nova_empresa(request):
    if not request.user.is_authenticated or request.user.is_superuser or request.user.user_type == UserType.ADMIN:
        return HttpResponseForbidden("Usuário não autorizado a criar empresas.")

    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.save(commit=False)
            empresa.organizacao = request.user.organizacao
            empresa.usuario = request.user
            empresa.save()
            form.save_m2m()
            status_code = 201 if request.headers.get("HX-Request") else 302
            return JsonResponse({"message": "Empresa criada com sucesso."}, status=status_code)
    else:
        form = EmpresaForm()

    return render(request, "empresas/nova.html", {"form": form})


# ------------------------------------------------------------------
# EDITAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if not pode_crud_empresa(request.user, empresa):
        return HttpResponseForbidden("Usuário não autorizado a editar esta empresa.")

    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return JsonResponse({"message": "Empresa atualizada com sucesso."}, status=200)
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
    empresas = Empresa.objects.select_related("usuario", "organizacao").prefetch_related("tags")
    if not request.user.is_superuser:
        empresas = empresas.filter(usuario__organizacao=request.user.organizacao)
    if query:
        palavras = [p.strip() for p in query.split() if p.strip()]
        q_objects = Q()
        for palavra in palavras:
            q_objects |= Q(tags__nome__icontains=palavra)
            q_objects |= Q(palavras_chave__icontains=palavra)
            q_objects |= Q(nome__icontains=palavra)
            q_objects |= Q(descricao__icontains=palavra)
            q_objects |= Q(cnpj__icontains=palavra)
            q_objects |= Q(municipio__icontains=palavra) | Q(estado__icontains=palavra)
            q_objects |= Q(tipo__icontains=palavra)
        empresas = empresas.filter(q_objects)
    empresas = empresas.distinct()
    template = "empresas/includes/empresas_table.html" if request.headers.get("HX-Request") else "empresas/busca.html"
    context = {"empresas": empresas, "q": query, "is_paginated": False}
    return render(request, template, context)


class TagListView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, ListView):
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


class TagCreateView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item criado com sucesso.")
        return super().form_valid(form)


class TagUpdateView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item atualizado com sucesso.")
        return super().form_valid(form)


class TagDeleteView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, DeleteView):
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
        and empresa.usuario.organizacao != request.user.organizacao  # Corrigido para usar 'organizacao'
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


# ------------------------------------------------------------------
# CRIAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def criar_empresa(request):
    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.save(commit=False)
            empresa.usuario = request.user
            empresa.save()
            form.save_m2m()
            messages.success(request, "Empresa criada com sucesso.")
            return redirect("empresas:lista")
    else:
        form = EmpresaForm()

    return render(request, "empresas/nova.html", {"form": form})


# ------------------------------------------------------------------
# DELETAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def remover_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if not pode_crud_empresa(request.user, empresa):
        return HttpResponseForbidden("Usuário não autorizado a remover esta empresa.")

    if request.method == "POST":
        empresa.delete()
        if request.headers.get("HX-Request"):
            return JsonResponse({"message": "Empresa removida com sucesso."}, status=204)
        return redirect("empresas:lista")

    return render(request, "empresas/confirmar_remocao.html", {"empresa": empresa})


@login_required
@no_superadmin_required
def adicionar_contato(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not pode_crud_empresa(request.user, empresa):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ContatoEmpresaForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.empresa = empresa
            contato.save()
            return JsonResponse({"message": "Contato adicionado"}, status=HTTP_201_CREATED)
    else:
        form = ContatoEmpresaForm()
    return render(request, "empresas/contato_form.html", {"form": form, "empresa": empresa})


@login_required
@no_superadmin_required
def editar_contato(request, pk):
    contato = get_object_or_404(ContatoEmpresa, pk=pk)
    if not pode_crud_empresa(request.user, contato.empresa):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ContatoEmpresaForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            return JsonResponse({"message": "Contato atualizado"}, status=200)
    else:
        form = ContatoEmpresaForm(instance=contato)
    return render(request, "empresas/contato_form.html", {"form": form, "empresa": contato.empresa})


@login_required
@no_superadmin_required
def remover_contato(request, pk):
    contato = get_object_or_404(ContatoEmpresa, pk=pk)
    if not pode_crud_empresa(request.user, contato.empresa):
        return HttpResponseForbidden()
    if request.method == "POST":
        contato.delete()
        return JsonResponse({}, status=HTTP_204_NO_CONTENT)
    return render(request, "empresas/contato_confirm_delete.html", {"contato": contato})
