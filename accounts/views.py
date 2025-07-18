from django.contrib.auth import (get_user_model, login, logout,
                                 update_session_auth_hash)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsAdmin, IsCoordenador
from accounts.serializers import UserSerializer

User = get_user_model()
import os
import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile, File
from django.core.files.storage import default_storage
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from tokens.forms import TokenAcessoForm
from tokens.models import TokenAcesso

from .forms import (CustomUserCreationForm, InformacoesPessoaisForm, MediaForm,
                    NotificacoesForm, RedesSociaisForm, CustomUserChangeForm)
from .models import NotificationSettings, UserMedia, cpf_validator

# ====================== PERFIL ======================


@login_required
def perfil_home(request):
    return redirect("accounts:informacoes_pessoais")


@login_required
def perfil_informacoes(request):
    if request.method == "POST":
        form = InformacoesPessoaisForm(
            request.POST, request.FILES, instance=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Informações pessoais atualizadas.")
            return redirect("accounts:informacoes_pessoais")
    else:
        form = InformacoesPessoaisForm(instance=request.user)

    return render(request, "perfil/informacoes_pessoais.html", {"form": form})


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


@login_required
def perfil_seguranca(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Senha alterada com sucesso.")
            return redirect("accounts:seguranca")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "perfil/seguranca.html", {"form": form})


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


@login_required
def perfil_conexoes(request):
    connections = (
        request.user.connections.all() if hasattr(request.user, "connections") else []
    )
    connection_requests = []  # pode ser implementado futuramente

    context = {
        "connections": connections,
        "connection_requests": connection_requests,
    }

    return render(request, "perfil/conexoes.html", context)


@login_required
def remover_conexao(request, id):
    try:
        other_user = User.objects.get(id=id)
        request.user.connections.remove(other_user)
        messages.success(request, f"Conexão com {other_user.get_full_name()} removida.")
    except User.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
    return redirect("accounts:conexoes")


@login_required
def perfil_midias(request):
    show_form = request.GET.get("adicionar") == "1" or request.method == "POST"
    q = request.GET.get("q", "").strip()

    if request.method == "POST":
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.user = request.user
            media.save()
            form.save_m2m()
            messages.success(request, "Arquivo enviado com sucesso.")
            return redirect("accounts:midias")
    else:
        form = MediaForm()

    medias = request.user.medias.order_by("-uploaded_at")
    if q:
        medias = medias.filter(
            Q(descricao__icontains=q) | Q(tags__nome__icontains=q)
        ).distinct()

    return render(
        request,
        "perfil/midias.html",
        {
            "form": form,
            "medias": medias,
            "show_form": show_form,
            "q": q,
        },
    )


@login_required
def perfil_midia_detail(request, pk):
    media = get_object_or_404(UserMedia, pk=pk, user=request.user)
    return render(request, "perfil/midia_detail.html", {"media": media})


@login_required
def perfil_midia_edit(request, pk):
    media = get_object_or_404(UserMedia, pk=pk, user=request.user)
    if request.method == "POST":
        form = MediaForm(request.POST, request.FILES, instance=media)
        if form.is_valid():
            form.save()
            messages.success(request, "Mídia atualizada com sucesso.")
            return redirect("accounts:midias")
    else:
        form = MediaForm(instance=media)

    return render(request, "perfil/midia_form.html", {"form": form})


@login_required
def perfil_midia_delete(request, pk):
    media = get_object_or_404(UserMedia, pk=pk, user=request.user)
    if request.method == "POST":
        media.delete()
        messages.success(request, "Mídia removida.")
        return redirect("accounts:midias")
    return render(request, "perfil/midia_confirm_delete.html", {"media": media})


# ====================== AUTENTICAÇÃO ======================


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:perfil")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("accounts:perfil")

    return render(request, "login/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


def register_view(request):
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
    return render(request, "login/login.html")


def onboarding(request):
    return render(request, "register/onboarding.html")


# ====================== REGISTRO MULTIETAPAS ======================


def nome(request):
    if request.method == "POST":
        nome_val = request.POST.get("nome")
        if nome_val:
            request.session["nome"] = nome_val
            return redirect("accounts:cpf")
    return render(request, "register/nome.html")


def cpf(request):
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
        token_code = request.session.get("invite_token")
        try:
            token_obj = TokenAcesso.objects.get(
                codigo=token_code, estado=TokenAcesso.Estado.NAO_USADO
            )
        except TokenAcesso.DoesNotExist:
            messages.error(request, "Token inválido.")
            return redirect("tokens:token")
        if token_obj.data_expiracao < timezone.now():
            token_obj.estado = TokenAcesso.Estado.EXPIRADO
            token_obj.save(update_fields=["estado"])
            messages.error(request, "Token expirado.")
            return redirect("tokens:token")

        username = request.session.get("usuario")
        email_val = request.session.get("email")
        pwd_hash = request.session.get("senha_hash")
        cpf_val = request.session.get("cpf")
        nome_parts = request.session.get("nome", "").split()
        first_name = nome_parts[0] if nome_parts else ""
        last_name = " ".join(nome_parts[1:]) if len(nome_parts) > 1 else ""

        if username and pwd_hash:
            tipo_mapping = {
                TokenAcesso.Tipo.ADMIN: User.Tipo.ADMIN,
                TokenAcesso.Tipo.GERENTE: User.Tipo.GERENTE,
                TokenAcesso.Tipo.CLIENTE: User.Tipo.CLIENTE,
            }
            user = User.objects.create(
                username=username,
                email=email_val,
                first_name=first_name,
                last_name=last_name,
                password=pwd_hash,
                cpf=cpf_val,
                tipo_id=tipo_mapping[token_obj.tipo_destino],
            )
            if token_obj.nucleo_destino:
                user.nucleo = token_obj.nucleo_destino
                user.save(update_fields=["nucleo"])
            foto_path = request.session.get("foto")
            if foto_path:
                with default_storage.open(foto_path, "rb") as f:
                    user.avatar.save(os.path.basename(foto_path), File(f))
                default_storage.delete(foto_path)
                del request.session["foto"]

            token_obj.estado = TokenAcesso.Estado.USADO
            token_obj.save(update_fields=["estado"])

            login(request, user)
            request.session["termos"] = True
            return redirect("accounts:perfil")

        messages.error(request, "Erro ao criar usuário. Tente novamente.")
        return redirect("accounts:usuario")

    return render(request, "register/termos.html")


def registro_sucesso(request):
    return render(request, "register/registro_sucesso.html")


@login_required
def perfil_home(request):
    user = request.user
    context = {
        "user": user,
        "connections": getattr(user, "connections", []).all(),
        "medias": user.medias.all(),
        "notifications": NotificationSettings.objects.filter(user=user).first(),
    }
    return render(request, "perfil/detail.html", context)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            if self.request.user.get_tipo_usuario == 'admin':
                self.permission_classes.append(IsAdmin)
            elif self.request.user.get_tipo_usuario == 'coordenador':
                self.permission_classes.append(IsCoordenador)
        return super().get_permissions()

    def perform_create(self, serializer):
        organizacao = self.request.user.organizacao
        if self.request.user.get_tipo_usuario == 'admin':
            serializer.save(organizacao=organizacao)
        elif self.request.user.get_tipo_usuario == 'coordenador':
            serializer.save(organizacao=organizacao, is_associado=False, is_staff=False)
        else:
            raise PermissionError("Você não tem permissão para criar usuários.")

class RegisterView(View):
    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("user_profile")
        return render(request, "accounts/register.html", {"form": form})

class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        form = CustomUserChangeForm(instance=request.user)
        return render(request, "accounts/user_profile.html", {"form": form})

    def post(self, request):
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("user_profile")
        return render(request, "accounts/user_profile.html", {"form": form})

class ChangePasswordView(LoginRequiredMixin, View):
    def get(self, request):
        form = PasswordChangeForm(user=request.user)
        return render(request, "accounts/change_password.html", {"form": form})

    def post(self, request):
        form = PasswordChangeForm(data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return redirect("user_profile")
        return render(request, "accounts/change_password.html", {"form": form})
