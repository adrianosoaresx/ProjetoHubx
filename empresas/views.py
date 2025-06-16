from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from .forms import EmpresaForm
from .models import Empresa
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse



@login_required
def lista_empresas(request):
    # This view is now effectively replaced by the _minhas_empresas.html partial
    # and the logic within perfil_view if it were to handle all company display.
    # However, for now, it remains as a fallback or for direct access.
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
            return HttpResponseRedirect(reverse("perfil") + "#empresas")
        else:
            perfil = request.user
            notificacoes = request.user.notification_settings
            empresas = Empresa.objects.filter(usuario=request.user)
            return render(
                request,
                "perfil/perfil.html",
                {
                    "empresas": empresas,
                    "empresa_form": form,
                    "perfil": perfil,
                    "notificacoes": notificacoes,
                },
            )

    # GET request → redireciona para a seção de empresas
    return HttpResponseRedirect(reverse("perfil") + "#empresas")

@login_required
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            # Redirect back to the profile's companies section
            return redirect("perfil") + "#empresas"
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, "empresas/form.html", {"form": form, "empresa": empresa})


def buscar_empresas(request):
    query = request.GET.get("q", "")
    empresas = Empresa.objects.all()
    if query:
        palavras = [p.strip() for p in query.split() if p.strip()]
        # Filter by tags or keywords
        q_objects = Q()
        for palavra in palavras:
            q_objects |= Q(tags__nome__icontains=palavra)
            q_objects |= Q(palavras_chave__icontains=palavra)
            q_objects |= Q(nome__icontains=palavra) # Also search by company name
            q_objects |= Q(descricao__icontains=palavra) # Search in description
        empresas = empresas.filter(q_objects)
    empresas = empresas.distinct()
    return render(request, "empresas/busca.html", {"empresas": empresas, "q": query})
