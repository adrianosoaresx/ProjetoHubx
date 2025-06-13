from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EmpresaForm
from .models import Empresa


@login_required
def lista_empresas(request):
    empresas = Empresa.objects.filter(usuario=request.user)
    return render(request, "empresas/lista.html", {"empresas": empresas})


@login_required
def nova_empresa(request):
    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.save(commit=False)
            empresa.usuario = request.user
            empresa.save()
            form.save_m2m()
            return redirect("empresas:lista")
    else:
        form = EmpresaForm()
    return render(request, "empresas/form.html", {"form": form})


@login_required
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            return redirect("empresas:lista")
    else:
        form = EmpresaForm(instance=empresa)
    return render(
        request,
        "empresas/form.html",
        {"form": form, "empresa": empresa},
    )


def buscar_empresas(request):
    query = request.GET.get("q", "")
    empresas = Empresa.objects.all()
    if query:
        palavras = [p.strip() for p in query.split() if p.strip()]
        for palavra in palavras:
            empresas = empresas.filter(
                Q(tags__nome__icontains=palavra)
                | Q(palavras_chave__icontains=palavra)
            )
    empresas = empresas.distinct()
    return render(
        request,
        "empresas/busca.html",
        {"empresas": empresas, "q": query},
    )
