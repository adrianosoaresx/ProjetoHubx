from django.shortcuts import render


def perfil_view(request):
    return render(request, 'perfil/perfil.html')
