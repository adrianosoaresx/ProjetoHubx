import base64
import os
import uuid
from io import BytesIO

import pyotp
import qrcode
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile, File
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import UserType
from accounts.serializers import UserSerializer
from accounts.tasks import send_confirmation_email, send_password_reset_email
from core.permissions import IsAdmin, IsCoordenador
from tokens.models import TokenAcesso, TOTPDevice

from .forms import (
    CustomUserChangeForm,
    EmailLoginForm,
    InformacoesPessoaisForm,
    MediaForm,
    RedesSociaisForm,
)
from .models import AccountToken, SecurityEvent, UserMedia
from .validators import cpf_validator

User = get_user_model()

# ====================== PERFIL ======================


@login_required
def perfil_home(request):
    return redirect("accounts:informacoes_pessoais")


@login_required
def perfil_informacoes(request):
    if request.method == "POST":
        form = InformacoesPessoaisForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if getattr(form, "email_changed", False):
                messages.info(request, _("Confirme o novo e-mail enviado."))
            else:
                messages.success(request, _("Informações pessoais atualizadas."))
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
            SecurityEvent.objects.create(
                usuario=user,
                evento="senha_alterada",
                ip=request.META.get("REMOTE_ADDR"),
            )
            messages.success(request, "Senha alterada com sucesso.")
            return redirect("accounts:seguranca")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "perfil/seguranca.html", {"form": form})


@login_required
def perfil_notificacoes(request):
    """Redireciona para a aba de preferências centralizada em ConfiguracaoConta."""
    return redirect("configuracoes")


@login_required
def enable_2fa(request):
    if request.user.two_factor_enabled:
        return redirect("accounts:seguranca")
    secret = request.session.get("tmp_2fa_secret")
    if not secret:
        secret = pyotp.random_base32()
        request.session["tmp_2fa_secret"] = secret
    totp = pyotp.TOTP(secret)
    otp_uri = totp.provisioning_uri(name=request.user.email, issuer_name="HubX")
    img = qrcode.make(otp_uri)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    if request.method == "POST":
        code = request.POST.get("code")
        if code and totp.verify(code):
            user = request.user
            user.two_factor_secret = secret
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
            TOTPDevice.all_objects.update_or_create(
                usuario=user,
                defaults={
                    "secret": user.two_factor_secret,
                    "confirmado": True,
                    "deleted": False,
                    "deleted_at": None,
                },
            )
            del request.session["tmp_2fa_secret"]
            messages.success(request, _("Verificação em duas etapas ativada."))
            return redirect("accounts:seguranca")
        messages.error(request, _("Código inválido."))
    return render(request, "perfil/enable_2fa.html", {"qr_base64": qr_base64})


@login_required
def disable_2fa(request):
    if not request.user.two_factor_enabled:
        return redirect("accounts:seguranca")
    if request.method == "POST":
        code = request.POST.get("code")
        if code and pyotp.TOTP(request.user.two_factor_secret).verify(code):
            user = request.user
            user.two_factor_secret = None
            user.two_factor_enabled = False
            user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
            TOTPDevice.objects.filter(usuario=user).delete()
            messages.success(request, _("Verificação em duas etapas desativada."))
            return redirect("accounts:seguranca")
        messages.error(request, _("Código inválido."))
    return render(request, "perfil/disable_2fa.html")


def check_2fa(request):
    email = request.GET.get("email")
    enabled = False
    if email:
        try:
            user = User.objects.get(email__iexact=email)
            enabled = user.two_factor_enabled and TOTPDevice.objects.filter(usuario=user).exists()
        except User.DoesNotExist:
            pass
    return JsonResponse({"enabled": enabled})


@login_required
def perfil_conexoes(request):
    connections = request.user.connections.all() if hasattr(request.user, "connections") else []
    connection_requests = request.user.followers.all() if hasattr(request.user, "followers") else []

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
def aceitar_conexao(request, id):
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:conexoes")

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:conexoes")

    request.user.connections.add(other_user)
    request.user.followers.remove(other_user)
    messages.success(request, f"Conexão com {other_user.get_full_name()} aceita.")
    return redirect("accounts:conexoes")


@login_required
def recusar_conexao(request, id):
    try:
        other_user = User.objects.get(id=id)
    except User.DoesNotExist:
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:conexoes")

    if other_user not in request.user.followers.all():
        messages.error(request, "Solicitação de conexão não encontrada.")
        return redirect("accounts:conexoes")

    request.user.followers.remove(other_user)
    messages.success(request, f"Solicitação de conexão de {other_user.get_full_name()} recusada.")
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

    medias = request.user.medias.order_by("-created_at")
    if q:
        medias = medias.filter(Q(descricao__icontains=q) | Q(tags__nome__icontains=q)).distinct()

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
        media.delete(soft=False)
        messages.success(request, "Mídia removida.")
        return redirect("accounts:midias")
    return render(request, "perfil/midia_confirm_delete.html", {"media": media})


# ====================== AUTENTICAÇÃO ======================


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:perfil")

    form = EmailLoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("accounts:perfil")

    return render(request, "login/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def excluir_conta(request):
    """Permite que o usuário exclua sua própria conta."""
    if request.method == "POST":
        if request.POST.get("confirm") != "EXCLUIR":
            messages.error(request, _("Confirme digitando EXCLUIR."))
            return redirect("accounts:excluir_conta")
        with transaction.atomic():
            user = request.user
            user.delete()
            user.exclusao_confirmada = True
            user.is_active = False
            user.save(update_fields=["exclusao_confirmada", "is_active"])
            SecurityEvent.objects.create(
                usuario=user,
                evento="conta_excluida",
                ip=request.META.get("REMOTE_ADDR"),
            )
        logout(request)
        messages.success(request, _("Sua conta foi excluída com sucesso."))
        return redirect("core:home")
def password_reset(request):
    """Solicita redefinição de senha."""
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:  # pragma: no cover - feedback uniforme
                pass
            else:
                token = AccountToken.objects.create(
                    usuario=user,
                    tipo=AccountToken.Tipo.PASSWORD_RESET,
                    expires_at=timezone.now() + timezone.timedelta(hours=1),
                    ip_gerado=request.META.get("REMOTE_ADDR"),
                )
                send_password_reset_email.delay(token.id)
        messages.success(
            request,
            _("Se o e-mail estiver cadastrado, enviaremos instru\u00e7\u00f5es."),
        )
        return redirect("accounts:password_reset")

    return render(request, "accounts/password_reset.html")


def password_reset_confirm(request, code: str):
    """Define nova senha a partir de um token."""
    token = get_object_or_404(
        AccountToken,
        codigo=code,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
    )
    if token.expires_at < timezone.now() or token.used_at:
        SecurityEvent.objects.create(
            usuario=token.usuario,
            evento="senha_redefinicao_falha",
            ip=request.META.get("REMOTE_ADDR"),
        )
        messages.error(request, _("Token inv\u00e1lido ou expirado."))
        return redirect("accounts:password_reset")

    if request.method == "POST":
        form = SetPasswordForm(token.usuario, request.POST)
        if form.is_valid():
            form.save()
            user = token.usuario
            user.failed_login_attempts = 0
            user.lock_expires_at = None
            user.save(update_fields=["failed_login_attempts", "lock_expires_at"])
            token.used_at = timezone.now()
            token.save(update_fields=["used_at"])
            SecurityEvent.objects.create(
                usuario=user,
                evento="senha_redefinida",
                ip=request.META.get("REMOTE_ADDR"),
            )
            messages.success(request, _("Senha redefinida com sucesso."))
            return redirect("accounts:login")
    else:
        form = SetPasswordForm(token.usuario)

    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"form": form},
    )


def confirmar_email(request, token: str):
    """Valida token de confirmação de e-mail."""
    try:
        token_obj = AccountToken.objects.select_related("usuario").get(
            codigo=token,
            tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        )
    except AccountToken.DoesNotExist:
        return render(request, "accounts/email_confirm.html", {"status": "erro"})

    if token_obj.expires_at < timezone.now() or token_obj.used_at:
        SecurityEvent.objects.create(
            usuario=token_obj.usuario,
            evento="email_confirmacao_falha",
            ip=request.META.get("REMOTE_ADDR"),
        )
        return render(request, "accounts/email_confirm.html", {"status": "erro"})

    with transaction.atomic():
        user = token_obj.usuario
        user.is_active = True
        user.email_confirmed = True
        user.save(update_fields=["is_active", "email_confirmed"])
        token_obj.used_at = timezone.now()
        token_obj.save(update_fields=["used_at"])
        SecurityEvent.objects.create(
            usuario=user,
            evento="email_confirmado",
            ip=request.META.get("REMOTE_ADDR"),
        )
    return render(request, "accounts/email_confirm.html", {"status": "sucesso"})


def onboarding(request):
    return render(request, "register/onboarding.html")


def resend_confirmation(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            try:
                user = User.objects.get(
                    email__iexact=email,
                    is_active=False,
                    deleted=False,
                )
            except User.DoesNotExist:
                pass
            else:
                AccountToken.objects.filter(
                    usuario=user,
                    tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                    used_at__isnull=True,
                ).update(used_at=timezone.now())
                token = AccountToken.objects.create(
                    usuario=user,
                    tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                    expires_at=timezone.now() + timezone.timedelta(hours=24),
                    ip_gerado=request.META.get("REMOTE_ADDR"),
                )
                send_confirmation_email.delay(token.id)
        messages.success(
            request,
            _("Se o e-mail estiver cadastrado, enviaremos nova confirmação."),
        )
        return redirect("accounts:login")
    return render(request, "accounts/resend_confirmation.html")


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
                if User.objects.filter(cpf=valor).exists():
                    messages.error(request, _("CPF já cadastrado."))
                    return redirect("accounts:cpf")
                else:
                    request.session["cpf"] = valor
                    return redirect("accounts:email")
            except ValidationError:
                messages.error(request, "CPF inválido.")
    return render(request, "register/cpf.html")


def email(request):
    if request.method == "POST":
        val = request.POST.get("email")
        if val:
            if User.objects.filter(email__iexact=val).exists():
                messages.error(request, _("Este e-mail já está em uso."))
                return redirect("accounts:email")
            else:
                request.session["email"] = val
                return redirect("accounts:senha")
    return render(request, "register/email.html")


def usuario(request):
    if request.method == "POST":
        usr = request.POST.get("usuario")
        if usr:
            if User.objects.filter(username__iexact=usr).exists():
                messages.error(request, _("Nome de usuário já cadastrado."))
                return redirect("accounts:usuario")
            else:
                request.session["usuario"] = usr
                return redirect("accounts:nome")
    return render(request, "register/usuario.html")


def senha(request):
    if request.method == "POST":
        s1 = request.POST.get("senha")
        s2 = request.POST.get("confirmar_senha")
        if s1 and s1 == s2:
            try:
                validate_password(s1)
            except ValidationError as exc:
                for msg in exc.messages:
                    messages.error(request, msg)
            else:
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
            token_obj = TokenAcesso.objects.get(codigo=token_code, estado=TokenAcesso.Estado.NOVO)
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
        nome_completo = request.session.get("nome", "")
        nome_parts = nome_completo.split()
        first_name = nome_parts[0] if nome_parts else ""
        last_name = " ".join(nome_parts[1:]) if len(nome_parts) > 1 else ""

        if username and pwd_hash:
            tipo_mapping = {
                TokenAcesso.TipoUsuario.ADMIN: UserType.ADMIN,
                TokenAcesso.TipoUsuario.COORDENADOR: UserType.COORDENADOR,
                TokenAcesso.TipoUsuario.NUCLEADO: UserType.NUCLEADO,
                TokenAcesso.TipoUsuario.ASSOCIADO: UserType.ASSOCIADO,
                TokenAcesso.TipoUsuario.CONVIDADO: UserType.CONVIDADO,
            }
            try:
                with transaction.atomic():
                    user = User.objects.create(
                        username=username,
                        email=email_val,
                        first_name=first_name,
                        last_name=last_name,
                        nome_completo=nome_completo,
                        password=pwd_hash,
                        cpf=cpf_val,
                        user_type=tipo_mapping[token_obj.tipo_destino],
                        is_active=False,
                        email_confirmed=False,
                    )
            except IntegrityError:
                messages.error(
                    request,
                    _("Não foi possível criar o usuário. Dados já cadastrados."),
                )
                return redirect("accounts:usuario")

            primeiro_nucleo = token_obj.nucleos.first()
            if primeiro_nucleo:
                user.nucleo = primeiro_nucleo
                user.save(update_fields=["nucleo"])
            foto_path = request.session.get("foto")
            if foto_path:
                with default_storage.open(foto_path, "rb") as f:
                    user.avatar.save(os.path.basename(foto_path), File(f))
                default_storage.delete(foto_path)
                del request.session["foto"]

            token_obj.estado = TokenAcesso.Estado.USADO
            token_obj.save(update_fields=["estado"])

            token = AccountToken.objects.create(
                usuario=user,
                tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                expires_at=timezone.now() + timezone.timedelta(hours=24),
                ip_gerado=request.META.get("REMOTE_ADDR"),
            )
            send_confirmation_email.delay(token.id)

            login(request, user)
            request.session["termos"] = True
            return redirect("accounts:perfil")

        messages.error(request, "Erro ao criar usuário. Tente novamente.")
        return redirect("accounts:usuario")

    return render(request, "register/termos.html")


def registro_sucesso(request):
    return render(request, "register/registro_sucesso.html")


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            if self.request.user.get_tipo_usuario == "admin":
                self.permission_classes.append(IsAdmin)
            elif self.request.user.get_tipo_usuario == "coordenador":
                self.permission_classes.append(IsCoordenador)
        return super().get_permissions()

    def perform_create(self, serializer):
        organizacao = self.request.user.organizacao
        if self.request.user.get_tipo_usuario == "admin":
            serializer.save(organizacao=organizacao)
        elif self.request.user.get_tipo_usuario == "coordenador":
            serializer.save(organizacao=organizacao, is_associado=False, is_staff=False)
        else:
            raise PermissionError("Você não tem permissão para criar usuários.")


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
            SecurityEvent.objects.create(
                usuario=request.user,
                evento="senha_alterada",
                ip=request.META.get("REMOTE_ADDR"),
            )
            return redirect("user_profile")
        return render(request, "accounts/change_password.html", {"form": form})
