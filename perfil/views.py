from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from empresas.models import Empresa


@login_required
def perfil_view(request):
    empresas = Empresa.objects.filter(usuario=request.user)
    return render(request, 'perfil/perfil.html', {'empresas': empresas})
