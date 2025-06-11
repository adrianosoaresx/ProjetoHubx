<<<<<<< HEAD
import os
import django
=======
"""Views de autenticação e registro de usuários."""

from django.conf import settings

if not settings.configured:
    import os
    import sys
    import django

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()

>>>>>>> e57cf540df6d4c2db3b6680bb5c894111d86d40d
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from usuarios.services import create_user

def login_view(request):
    """Autentica o usuário utilizando credenciais de login."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("perfil")
        return render(
            request,
            "login/login.html",
            {"error": "Nome de usuário ou senha inválidos."},
        )

    return render(request, "login/login.html")

def password_reset(request):
    return render(request, 'login/login.html')

def onboarding(request):
    return render(request, 'register/onboarding.html')

def nome(request):
    if request.method == "POST":
        nome_value = request.POST.get('nome')
        if nome_value:
            request.session['nome'] = nome_value
            return redirect('custom_auth:email')
    return render(request, 'register/nome.html')

def email(request):
    if request.method == "POST":
        email_value = request.POST.get('email')
        if email_value:
            request.session['email'] = email_value
            return redirect('custom_auth:senha')
    return render(request, 'register/email.html')

def token(request):
    if request.method == "POST":
        token_value = request.POST.get('token')
        if token_value:  # validações aqui
            request.session['invite_token'] = token_value
            return redirect('custom_auth:usuario')

    return render(request, 'register/token.html')

def usuario(request):
    if request.method == "POST":
        usuario_value = request.POST.get('usuario')
        if usuario_value:
            request.session['usuario'] = usuario_value
            return redirect('custom_auth:nome')
    return render(request, 'register/usuario.html')

def senha(request):
    if request.method == "POST":
        senha1 = request.POST.get('senha1')
        senha2 = request.POST.get('senha2')
        if senha1 and senha1 == senha2:
            request.session['senha'] = senha1
            return redirect('custom_auth:foto')
    return render(request, 'register/senha.html')

def foto(request):
    if request.method == "POST":
        foto_file = request.FILES.get('foto')
        if foto_file:
            request.session['foto'] = foto_file.name
        return redirect('custom_auth:termos')
    return render(request, 'register/foto.html')

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

            if username and password:
                user = create_user(
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
                    return redirect("custom_auth:usuario")
            return redirect("custom_auth:usuario")

    return render(request, "register/termos.html")

def registro_sucesso(request):
    return render(request, 'register/registro_sucesso.html')
