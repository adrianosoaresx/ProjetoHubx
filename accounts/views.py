from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from empresas.models import Empresa


@login_required
def perfil_view(request):
    perfil = request.user
    notificacoes = request.user.notification_settings

    if request.method == "POST":
        perfil.bio = request.POST.get("bio", perfil.bio)
        perfil.telefone = request.POST.get("telefone", perfil.telefone)
        perfil.whatsapp = request.POST.get("whatsapp", perfil.whatsapp)
        perfil.endereco = request.POST.get("endereco", perfil.endereco)
        perfil.cidade = request.POST.get("cidade", perfil.cidade)
        perfil.estado = request.POST.get("estado", perfil.estado)
        perfil.cep = request.POST.get("cep", perfil.cep)
        perfil.facebook = request.POST.get("facebook", perfil.facebook)
        perfil.twitter = request.POST.get("twitter", perfil.twitter)
        perfil.instagram = request.POST.get("instagram", perfil.instagram)
        perfil.linkedin = request.POST.get("linkedin", perfil.linkedin)
        perfil.website = request.POST.get("website", perfil.website)
        perfil.idioma = request.POST.get("idioma", perfil.idioma)
        perfil.fuso_horario = request.POST.get("fuso_horario", perfil.fuso_horario)
        perfil.perfil_publico = bool(request.POST.get("perfil_publico"))
        perfil.mostrar_email = bool(request.POST.get("mostrar_email"))
        perfil.mostrar_telefone = bool(request.POST.get("mostrar_telefone"))
        if "avatar" in request.FILES:
            perfil.avatar = request.FILES["avatar"]
        perfil.save()

        notificacoes.email_conexoes = bool(request.POST.get("email_conexoes"))
        notificacoes.email_mensagens = bool(request.POST.get("email_mensagens"))
        notificacoes.email_eventos = bool(request.POST.get("email_eventos"))
        notificacoes.email_newsletter = bool(request.POST.get("email_newsletter"))
        notificacoes.sistema_conexoes = bool(request.POST.get("sistema_conexoes"))
        notificacoes.sistema_mensagens = bool(request.POST.get("sistema_mensagens"))
        notificacoes.sistema_eventos = bool(request.POST.get("sistema_eventos"))
        notificacoes.sistema_comentarios = bool(request.POST.get("sistema_comentarios"))
        notificacoes.save()

    empresas = Empresa.objects.filter(usuario=request.user)
    return render(
        request,
        "perfil/perfil.html",
        {"empresas": empresas, "perfil": perfil, "notificacoes": notificacoes},
    )
