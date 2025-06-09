from django.shortcuts import render
from django.http import HttpResponse

def perfil_view(request):
    return HttpResponse("Página do Perfil do Usuário")


