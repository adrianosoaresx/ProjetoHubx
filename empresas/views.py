
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from django.contrib import messages

from .models import Empresa
from .forms import EmpresaForm


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
