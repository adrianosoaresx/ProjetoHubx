from django.contrib.auth.decorators import login_required
from django.contrib.auth import (
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.hashers import make_password
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile, File
import os
import uuid

# ────────────────────────────────────────────────────────────────
# Forms usados nas abas do perfil
# ────────────────────────────────────────────────────────────────
from .forms import (
    InformacoesPessoaisForm,
    ContatoForm,
    RedesSociaisForm,
    ContaForm,
    NotificacoesForm,
    CustomUserCreationForm,
)
from .models import cpf_validator, NotificationSettings  # ajuste se necessário

User = get_user_model()

# =====================================================================
# PERFIL – cada aba usa um ModelForm dedicado
# =====================================================================

@login_required
def perfil_home(request):
    """Entrada do perfil → redireciona para Informações Pessoais."""
    return redirect("accounts:informacoes_pessoais")

# 1 • Informações Pessoais
@login_required
def perfil_informacoes(request):
    if request.method == "POST":
        form = InformacoesPessoaisForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Informações pessoais atualizadas.")
            return redirect("accounts:informacoes_pessoais")
    else:
        form = InformacoesPessoaisForm(instance=request.user)

    return render(request, "perfil/informacoes_pessoais.html", {"form": form})

# 2 • Contato
@login_required
def perfil_contato(request):
    if request.method == "POST":
        form = ContatoForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Informações de contato salvas.")
            return redirect("accounts:contato")
    else:
        form = ContatoForm(instance=request.user)

    return render(request, "perfil/contato.html", {"form": form})

# 3 • Redes Sociais
@login_required
def perfil_redes_sociais(request):
    if request.method == "POST":
        form = RedesSociaisForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Redes sociais atualizadas.")
            return redirect("accounts:redes_sociais")
    else:
        form = RedesSociaisForm(instance=request.user)

    return render(request, "perfil/redes_sociais.html", {"form": form})

# 4 • Segurança (troca de senha)
@login_required
def perfil_seguranca(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # mantém login
            messages.success(request, "Senha alterada com sucesso.")
            return redirect("accounts:seguranca")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "perfil/seguranca.html", {"form": form})

# 5 • Notificações
@login_required
def perfil_notificacoes(request):
    settings_obj, _ = NotificationSettings.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = NotificacoesForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferências de notificação salvas.")
            return redirect("accounts:notificacoes")
    else:
        form = NotificacoesForm(instance=settings_obj)

    return render(request, "perfil/notificacoes.html", {"form": form})

# 6 • Conexões (somente leitura)
@login_required
def perfil_conexoes(request):
    conexoes = getattr(request.user, "connections", None)
    seguidores = getattr(request.user, "followers", None)

    return render(
        request,
        "perfil/conexoes.html",
        {
            "conexoes": conexoes.all() if conexoes else [],
            "seguidores": seguidores.all() if seguidores else [],
        },
    )

# 7 • Configurações da Conta
@login_required
def perfil_conta(request):
    if request.method == "POST":
        form = ContaForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Configurações da conta atualizadas.")
            return redirect("accounts:conta")
    else:
        form = ContaForm(instance=request.user)

    return render(request, "perfil/conta.html", {"form": form})

# =====================================================================
# AUTENTICAÇÃO
# =====================================================================

def login_view(request):
    """Autentica o usuário usando o AuthenticationForm do Django."""
    if request.user.is_authenticated:
        return redirect("accounts:perfil")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("accounts:perfil")

    return render(request, "login/login.html", {"form": form})

def logout_view(request):
    """Encerra a sessão do usuário e volta para o login."""
    logout(request)
    return redirect("accounts:login")

def register_view(request):
    """Registro simples usando ``CustomUserCreationForm``."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("accounts:perfil")
    else:
        form = CustomUserCreationForm()

    return render(request, "register/onboarding.html", {"form": form})

def password_reset(request):
    # TODO: implementar fluxo real de reset de senha
    return render(request, "login/login.html")

def onboarding(request):
    return render(request, "register/onboarding.html")

# ------------------------------------------------------------------
# FLUXO DE REGISTRO EM VÁRIAS ETAPAS (nome → cpf → …)
# ------------------------------------------------------------------

def nome(request):
    if request.method == "POST":
        nome_val = request.POST.get("nome")
        if nome_val:
            request.session["nome"] = nome_val
            return redirect("accounts:cpf")
    return render(request, "register/nome.html")

def cpf(request):
    """Solicita o CPF logo após o nome."""
    if request.method == "POST":
        valor = request.POST.get("cpf")
        if valor:
            try:
                cpf_validator(valor)
                request.session["cpf"] = valor
                return redirect("accounts:email")
            except ValidationError:
                messages.error(request, "CPF inválido.")
    return render(request, "register/cpf.html")

def email(request):
    if request.method == "POST":
        val = request.POST.get("email")
        if val:
            request.session["email"] = val
            return redirect("accounts:senha")
    return render(request, "register/email.html")

def token(request):
    if request.method == "POST":
        tkn = request.POST.get("token")
        if tkn:
            request.session["invite_token"] = tkn
            return redirect("accounts:usuario")
    return render(request, "register/token.html")

def usuario(request):
    if request.method == "POST":
        usr = request.POST.get("usuario")
        if usr:
            request.session["usuario"] = usr
            return redirect("accounts:nome")
    return render(request, "register/usuario.html")

def senha(request):
    if request.method == "POST":
        s1 = request.POST.get("senha")
        s2 = request.POST.get("confirmar_senha")
        if s1 and s1 == s2:
            request.session["senha_hash"] = make_password(s1)
            return redirect("accounts:foto")
    return render(request, "register/senha.html")

def foto(request):
    if request.method == "POST":
        arquivo = request.FILES.get("foto")
        if arquivo:
            temp_name = f"temp/{uuid.uuid4()}_{arquivo.name}"
            path = default_storage.save(temp_name, ContentFile(arquivo.read()))
            request.session["foto"] = path
        return redirect("accounts:termos")
    return render(request, "register/foto.html")

def termos(request):
    if request.method == "POST" and request.POST.get("aceitar_termos"):
        # cria usuário com dados armazenados na sessão
        username = request.session.get("usuario")
        email_val = request.session.get("email")
        pwd_hash = request.session.get("senha_hash")
        cpf_val = request.session.get("cpf")
        nome_parts = request.session.get("nome", "").split()
        first_name = nome_parts[0] if nome_parts else ""
        last_name = " ".join(nome_parts[1:]) if len(nome_parts) > 1 else ""

        if username and pwd_hash:
            user = User.objects.create(
                username=username,
                email=email_val,
                first_name=first_name,
                last_name=last_name,
                password=pwd_hash,
                cpf=cpf_val,
            )
            # salva foto, se houver
            foto_path = request.session.get("foto")
            if foto_path:
                with default_storage.open(foto_path, "rb") as f:
                    user.avatar.save(os.path.basename(foto_path), File(f))
                default_storage.delete(foto_path)
                del request.session["foto"]

            login(request, user)
            request.session["termos"] = True
            return redirect("accounts:perfil")

        messages.error(request, "Erro ao criar usuário. Tente novamente.")
        return redirect("accounts:usuario")

    return render(request, "register/termos.html")

def registro_sucesso(request):
    return render(request, "register/registro_sucesso.html")
