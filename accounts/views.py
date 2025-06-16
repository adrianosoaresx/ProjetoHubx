from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile, File
import os
import uuid

from .forms import CustomUserCreationForm
from empresas.models import Empresa
from empresas.forms import EmpresaForm
from .models import cpf_validator

User = get_user_model()


@login_required
def perfil_view(request):
    perfil = request.user
    notificacoes = request.user.notification_settings

    if request.method == "POST":
        # Dados basicos
        nome_completo = request.POST.get("nome")
        if nome_completo:
            partes = nome_completo.split()
            perfil.first_name = partes[0]
            perfil.last_name = " ".join(partes[1:]) if len(partes) > 1 else ""
        perfil.username = request.POST.get("username", perfil.username)
        perfil.email = request.POST.get("email", perfil.email)
        perfil.bio = request.POST.get("bio", perfil.bio)
        perfil.data_nascimento = request.POST.get("data_nascimento", perfil.data_nascimento)
        perfil.genero = request.POST.get("genero", perfil.genero)

        # Contato e endereco
        perfil.telefone = request.POST.get("telefone", perfil.telefone)
        perfil.whatsapp = request.POST.get("whatsapp", perfil.whatsapp)
        perfil.endereco = request.POST.get("endereco", perfil.endereco)
        perfil.cidade = request.POST.get("cidade", perfil.cidade)
        perfil.estado = request.POST.get("estado", perfil.estado)
        perfil.cep = request.POST.get("cep", perfil.cep)

        # Redes sociais e preferencias
        perfil.facebook = request.POST.get("facebook", perfil.facebook)
        perfil.twitter = request.POST.get("twitter", perfil.twitter)
        perfil.instagram = request.POST.get("instagram", perfil.instagram)
        perfil.linkedin = request.POST.get("linkedin", perfil.linkedin)
        perfil.website = request.POST.get("website", perfil.website)
        perfil.idioma = request.POST.get("idioma", perfil.idioma)
        perfil.fuso_horario = request.POST.get("fuso_horario", perfil.fuso_horario)

        if "perfil_publico" in request.POST:
            perfil.perfil_publico = bool(request.POST.get("perfil_publico"))
        if "mostrar_email" in request.POST:
            perfil.mostrar_email = bool(request.POST.get("mostrar_email"))
        if "mostrar_telefone" in request.POST:
            perfil.mostrar_telefone = bool(request.POST.get("mostrar_telefone"))

        if "avatar" in request.FILES:
            perfil.avatar = request.FILES["avatar"]
        if "remover_avatar" in request.POST:
            perfil.avatar.delete(save=False)
            perfil.avatar = None

        perfil.save()

        if "email_conexoes" in request.POST:
            notificacoes.email_conexoes = bool(request.POST.get("email_conexoes"))
        if "email_mensagens" in request.POST:
            notificacoes.email_mensagens = bool(request.POST.get("email_mensagens"))
        if "email_eventos" in request.POST:
            notificacoes.email_eventos = bool(request.POST.get("email_eventos"))
        if "email_newsletter" in request.POST:
            notificacoes.email_newsletter = bool(request.POST.get("email_newsletter"))
        if "sistema_conexoes" in request.POST:
            notificacoes.sistema_conexoes = bool(request.POST.get("sistema_conexoes"))
        if "sistema_mensagens" in request.POST:
            notificacoes.sistema_mensagens = bool(request.POST.get("sistema_mensagens"))
        if "sistema_eventos" in request.POST:
            notificacoes.sistema_eventos = bool(request.POST.get("sistema_eventos"))
        if "sistema_comentarios" in request.POST:
            notificacoes.sistema_comentarios = bool(request.POST.get("sistema_comentarios"))
        notificacoes.save()

    empresas = Empresa.objects.filter(usuario=request.user)
    empresa_form = EmpresaForm()
    return render(
        request,
        "perfil/perfil.html",
        {
            "empresas": empresas,
            "empresa_form": empresa_form,
            "perfil": perfil,
            "notificacoes": notificacoes,
        },
    )


def login_view(request):
    """Autentica o usuário utilizando ``AuthenticationForm`` do Django."""
    if request.user.is_authenticated:
        return redirect("perfil")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("perfil")
    else:
        form = AuthenticationForm(request)

    return render(request, "login/login.html", {"form": form})


def logout_view(request):
    """Encerra a sessão do usuário e redireciona para a tela de login."""
    logout(request)
    return redirect("accounts:login")


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
            return redirect("accounts:cpf")
    return render(request, "register/nome.html")


def cpf(request):
    """Solicita o CPF logo apos o nome completo."""
    if request.method == "POST":
        cpf_value = request.POST.get("cpf")
        if cpf_value:
            try:
                cpf_validator(cpf_value)
                request.session["cpf"] = cpf_value
                return redirect("accounts:email")
            except ValidationError:
                pass
    return render(request, "register/cpf.html")


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
            request.session["senha_hash"] = make_password(senha1)
            return redirect("accounts:foto")
    return render(request, "register/senha.html")


def foto(request):
    if request.method == "POST":
        foto_file = request.FILES.get("foto")
        if foto_file:
            temp_name = f"temp/{uuid.uuid4()}_{foto_file.name}"
            path = default_storage.save(temp_name, ContentFile(foto_file.read()))
            request.session["foto"] = path
        return redirect("accounts:termos")
    return render(request, "register/foto.html")


def termos(request):
    if request.method == "POST":
        if request.POST.get("aceitar_termos"):
            request.session["termos"] = True

            # Cria o usuario usando os dados armazenados na sessao
            username = request.session.get("usuario")
            email = request.session.get("email")
            password_hash = request.session.get("senha_hash")
            cpf = request.session.get("cpf")
            nome = request.session.get("nome", "").split()
            first_name = nome[0] if nome else ""
            last_name = " ".join(nome[1:]) if len(nome) > 1 else ""
            # ...

            if username and password_hash:
                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password_hash,
                    cpf=cpf,
                )
                user.save()
                foto_path = request.session.get("foto")
                if foto_path:
                    with default_storage.open(foto_path, "rb") as f:
                        user.avatar.save(os.path.basename(foto_path), File(f))
                    default_storage.delete(foto_path)
                    del request.session["foto"]
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



