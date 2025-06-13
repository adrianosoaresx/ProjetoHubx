from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect

from .forms import CustomUserCreationForm
from empresas.models import Empresa

User = get_user_model()


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


def login_view(request):
    """Autentica o usuário utilizando ``AuthenticationForm`` do Django."""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("perfil")
    else:
        form = AuthenticationForm(request)

    return render(request, "login/login.html", {"form": form})


def password_reset(request):
    return render(request, "login/login.html")


def register_view(request):
    """Registra um novo usuário usando ``CustomUserCreationForm``."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("perfil")
    else:
        form = CustomUserCreationForm()

    return render(request, "register/register_form.html", {"form": form})


def onboarding(request):
    return render(request, "register/onboarding.html")


def nome(request):
    if request.method == "POST":
        nome_value = request.POST.get("nome")
        if nome_value:
            request.session["nome"] = nome_value
            return redirect("accounts:email")
    return render(request, "register/nome.html")


def email(request):
    if request.method == "POST":
        email_value = request.POST.get("email")
        if email_value:
            request.session["email"] = email_value
            return redirect("accounts:senha")
    return render(request, "register/email.html")


def token(request):
    if request.method == "POST":
        token_value = request.POST.get("token")
        if token_value:  # validações aqui
            request.session["invite_token"] = token_value
            return redirect("accounts:usuario")

    return render(request, "register/token.html")


def usuario(request):
    if request.method == "POST":
        usuario_value = request.POST.get("usuario")
        if usuario_value:
            request.session["usuario"] = usuario_value
            return redirect("accounts:nome")
    return render(request, "register/usuario.html")


def senha(request):
    if request.method == "POST":
        senha1 = request.POST.get("senha")
        senha2 = request.POST.get("confirmar_senha")
        if senha1 and senha1 == senha2:
            request.session["senha"] = senha1
            return redirect("accounts:foto")
    return render(request, "register/senha.html")


def foto(request):
    if request.method == "POST":
        foto_file = request.FILES.get("foto")
        if foto_file:
            request.session["foto"] = foto_file.name
        return redirect("accounts:termos")
    return render(request, "register/foto.html")


def termos(request):
    if request.method == "POST":
        if request.POST.get("aceitar_termos"):
            request.session["termos"] = True

            # Cria o usuario usando os dados armazenados na sessao
            username = request.session.get("usuario")
            email = request.session.get("email")
            password = request.session.get("senha")
            nome = request.session.get("nome", "").split()
            first_name = nome[0] if nome else ""
            last_name = " ".join(nome[1:]) if len(nome) > 1 else ""
            # ...

            if username and password:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                if user:
                    login(request, user)
                    return redirect("perfil")
                else:
                    # Username already exists; ask user to escolher outro
                    return redirect("accounts:usuario")
            return redirect("accounts:usuario")

    return render(request, "register/termos.html")


def registro_sucesso(request):
    return render(request, "register/registro_sucesso.html")



