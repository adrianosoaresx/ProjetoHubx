from __future__ import annotations

import base64
import hashlib
from io import BytesIO

import pyotp
import qrcode
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

from accounts.models import SecurityEvent
from notificacoes.services.email_client import send_email
from notificacoes.services.whatsapp_client import send_whatsapp

from .forms import (
    Ativar2FAForm,
    GerarCodigoAutenticacaoForm,
    GerarApiTokenForm,
    GerarTokenConviteForm,
    ValidarCodigoAutenticacaoForm,
    ValidarTokenConviteForm,
)
from .metrics import tokens_invites_revoked_total
from .models import (
    ApiToken,
    ApiTokenLog,
    CodigoAutenticacaoLog,
    TokenAcesso,
    TokenUsoLog,
    TOTPDevice,
)
from .perms import can_issue_invite
from .services import (
    create_invite_token,
    generate_token,
    list_tokens,
    revoke_token,
)
from .utils import get_client_ip


User = get_user_model()


def token(request):
    if request.method == "POST":
        tkn = request.POST.get("token")
        if tkn:
            request.session["invite_token"] = tkn
            return redirect("accounts:usuario")
    return render(request, "register/token.html")



@login_required
def listar_convites(request):
    if not request.user.is_staff:
        messages.error(request, _("Você não tem permissão para visualizar convites."))
        return redirect("accounts:perfil")
    convites = TokenAcesso.objects.filter(gerado_por=request.user)
    return render(request, "tokens/listar_convites.html", {"convites": convites})


@login_required
def revogar_convite(request, token_id: int):
    if not request.user.is_staff:
        messages.error(request, _("Você não tem permissão para revogar convites."))
        return redirect("tokens:listar_convites")
    token = get_object_or_404(TokenAcesso, id=token_id, gerado_por=request.user)
    if token.estado != TokenAcesso.Estado.REVOGADO:
        now = timezone.now()
        token.estado = TokenAcesso.Estado.REVOGADO
        token.revogado_em = now
        token.revogado_por = request.user
        token.save(update_fields=["estado", "revogado_em", "revogado_por"])
        TokenUsoLog.objects.create(
            token=token,
            usuario=request.user,
            acao=TokenUsoLog.Acao.REVOGACAO,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        tokens_invites_revoked_total.inc()
        messages.success(request, _("Convite revogado."))
    else:
        messages.info(request, _("Convite já estava revogado."))
    return redirect("tokens:listar_convites")


@login_required
def listar_api_tokens(request):
    tokens = list_tokens(request.user)
    form = GerarApiTokenForm()
    return render(request, "tokens/api_tokens.html", {"tokens": tokens, "form": form})


@login_required
def revogar_api_token(request, token_id: str):
    token = get_object_or_404(ApiToken, id=token_id, user=request.user)
    if token.revoked_at:
        messages.info(request, _("Token já revogado."))
    else:
        revoke_token(token.id, revogado_por=request.user)
        ApiTokenLog.objects.create(
            token=token,
            usuario=request.user,
            acao=ApiTokenLog.Acao.REVOGACAO,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        messages.success(request, _("Token revogado."))
    return redirect("tokens:listar_api_tokens")


@login_required
def gerar_api_token(request):
    if request.method != "POST":
        tokens = list_tokens(request.user)
        form = GerarApiTokenForm()
        messages.error(request, _("Método não permitido"))
        return render(
            request,
            "tokens/api_tokens.html",
            {"tokens": tokens, "form": form},
            status=405,
        )

    form = GerarApiTokenForm(request.POST)
    if form.is_valid():
        scope = form.cleaned_data["scope"]
        if scope == "admin" and not request.user.is_superuser:
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "tokens/_resultado.html",
                    {"error": _("Não autorizado")},
                    status=403,
                )
            messages.error(request, _("Não autorizado"))
            tokens = list_tokens(request.user)
            return render(
                request,
                "tokens/api_tokens.html",
                {"tokens": tokens, "form": form, "error": _("Não autorizado")},
                status=403,
            )

        client_name = form.cleaned_data["client_name"]
        expires_in = form.cleaned_data.get("expires_in")
        expires_delta = timezone.timedelta(days=expires_in) if expires_in else None

        raw_token = generate_token(request.user, client_name, scope, expires_delta)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = ApiToken.objects.get(token_hash=token_hash)
        ApiTokenLog.objects.create(
            token=token,
            usuario=request.user,
            acao=ApiTokenLog.Acao.GERACAO,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"token": raw_token})
        messages.success(request, _("Token gerado"))
        tokens = list_tokens(request.user)
        form = GerarApiTokenForm()
        return render(
            request,
            "tokens/api_tokens.html",
            {"tokens": tokens, "form": form, "token": raw_token},
        )

    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "tokens/_resultado.html",
            {"error": _("Dados inválidos")},
            status=400,
        )
    messages.error(request, _("Dados inválidos"))
    tokens = list_tokens(request.user)
    return render(
        request,
        "tokens/api_tokens.html",
        {"tokens": tokens, "form": form, "error": _("Dados inválidos")},
        status=400,
    )


class GerarTokenConviteView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        choices = [
            choice
            for choice in TokenAcesso.TipoUsuario.choices
            if can_issue_invite(request.user, choice[0])
        ]
        if not choices:
            messages.error(
                request,
                _("Seu perfil não permite gerar convites."),
            )
            return redirect("accounts:perfil")
        form = GerarTokenConviteForm(user=request.user)
        form.fields["tipo_destino"].choices = choices
        return render(request, "tokens/gerar_token.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = GerarTokenConviteForm(request.POST, user=request.user)
        choices = [
            choice
            for choice in TokenAcesso.TipoUsuario.choices
            if can_issue_invite(request.user, choice[0])
        ]
        form.fields["tipo_destino"].choices = choices
        if form.is_valid():
            target_role = form.cleaned_data["tipo_destino"]
            if not can_issue_invite(request.user, target_role):
                if request.headers.get("HX-Request") == "true":
                    return render(
                        request,
                        "tokens/_resultado.html",
                        {"error": _("Seu perfil não permite gerar convites para este tipo de usuário.")},
                        status=403,
                    )
                messages.error(
                    request,
                    _("Seu perfil não permite gerar convites para este tipo de usuário."),
                )
                return render(
                    request,
                    "tokens/gerar_token.html",
                    {"form": form, "error": _("Seu perfil não permite gerar convites para este tipo de usuário.")},
                    status=403,
                )

            start_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_day = start_day + timezone.timedelta(days=1)
            if (
                TokenAcesso.objects.filter(
                    gerado_por=request.user,
                    created_at__gte=start_day,
                    created_at__lt=end_day,
                ).count()
                >= 5
            ):
                if request.headers.get("HX-Request") == "true":
                    return render(
                        request,
                        "tokens/_resultado.html",
                        {"error": _("Limite diário atingido.")},
                        status=429,
                    )
                messages.error(request, _("Limite diário atingido."))
                return render(
                    request,
                    "tokens/gerar_token.html",
                    {"form": form, "error": _("Limite diário atingido.")},
                    status=429,
                )

            token, codigo = create_invite_token(
                gerado_por=request.user,
                tipo_destino=target_role,
                data_expiracao=timezone.now() + timezone.timedelta(days=30),
                organizacao=form.cleaned_data.get("organizacao"),
                nucleos=form.cleaned_data["nucleos"],
            )

            ip = get_client_ip(request)
            token.ip_gerado = ip
            token.save(update_fields=["ip_gerado"])
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.GERACAO,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            token.codigo = codigo

            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"token": codigo})
            messages.success(request, _("Token gerado"))
            form = GerarTokenConviteForm(user=request.user)
            form.fields["tipo_destino"].choices = choices
            return render(
                request,
                "tokens/gerar_token.html",
                {"form": form, "token": codigo},
            )
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "tokens/_resultado.html",
                {"error": _("Dados inválidos")},
                status=400,
            )
        messages.error(request, _("Dados inválidos"))
        return render(
            request,
            "tokens/gerar_token.html",
            {"form": form, "error": _("Dados inválidos")},
            status=400,
        )


class ValidarTokenConviteView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = ValidarTokenConviteForm()
        return render(request, "tokens/validar_token.html", {"form": form})
    def post(self, request, *args, **kwargs):
        form = ValidarTokenConviteForm(request.POST)
        if form.is_valid():
            token = form.token
            token.usuario = request.user
            token.estado = TokenAcesso.Estado.USADO
            ip = get_client_ip(request)
            token.ip_utilizado = ip
            token.save(update_fields=["usuario", "estado", "ip_utilizado"])
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.USO,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": _("Token validado")})
            messages.success(request, _("Token validado"))
            form = ValidarTokenConviteForm()
            return render(
                request,
                "tokens/validar_token.html",
                {"form": form, "success": _("Token validado")},
            )
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "tokens/_resultado.html",
                {"error": form.errors.as_text()},
                status=400,
            )
        messages.error(request, form.errors.as_text())
        return render(
            request,
            "tokens/validar_token.html",
            {"form": form, "error": form.errors.as_text()},
            status=400,
        )


class GerarCodigoAutenticacaoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = GerarCodigoAutenticacaoForm()
        return render(request, "tokens/gerar_codigo_autenticacao.html", {"form": form})
    def post(self, request, *args, **kwargs):
        form = GerarCodigoAutenticacaoForm(request.POST, usuario=request.user)
        if form.is_valid():
            codigo = form.save()
            ip = get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            log = CodigoAutenticacaoLog.objects.create(
                codigo=codigo,
                usuario=request.user,
                acao=CodigoAutenticacaoLog.Acao.EMISSAO,
                ip=ip,
                user_agent=user_agent,
            )
            email_ok = sms_ok = False
            erros: list[str] = []
            subject = _("Código de autenticação")
            body = _("Seu código de autenticação é %(codigo)s") % {"codigo": codigo.codigo}
            if getattr(request.user, "email", ""):
                try:
                    send_email(request.user, subject, body)
                    email_ok = True
                except Exception as exc:  # pragma: no cover - integração externa
                    erros.append(f"email: {exc}")
            if getattr(request.user, "whatsapp", ""):
                try:
                    send_whatsapp(request.user, body)
                    sms_ok = True
                except Exception as exc:  # pragma: no cover - integração externa
                    erros.append(f"sms: {exc}")
            log.status_envio = (
                CodigoAutenticacaoLog.StatusEnvio.SUCESSO
                if email_ok or sms_ok
                else CodigoAutenticacaoLog.StatusEnvio.FALHA
            )
            if erros:
                log.mensagem_envio = "; ".join(str(e) for e in erros)
            log.save(update_fields=["status_envio", "mensagem_envio"])
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"codigo": codigo.codigo})
            messages.success(request, _("Código gerado"))
            form = GerarCodigoAutenticacaoForm()
            return render(
                request,
                "tokens/gerar_codigo_autenticacao.html",
                {"form": form, "codigo": codigo.codigo},
            )
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "tokens/_resultado.html",
                {"error": _("Dados inválidos")},
                status=400,
            )
        messages.error(request, _("Dados inválidos"))
        return render(
            request,
            "tokens/gerar_codigo_autenticacao.html",
            {"form": form, "error": _("Dados inválidos")},
            status=400,
        )


class ValidarCodigoAutenticacaoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        form = ValidarCodigoAutenticacaoForm(usuario=request.user)
        return render(request, "tokens/validar_codigo_autenticacao.html", {"form": form})
    def post(self, request, *args, **kwargs):
        form = ValidarCodigoAutenticacaoForm(request.POST, usuario=request.user)
        if form.is_valid():
            ip = get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            codigo = getattr(form, "codigo_obj", None)
            if codigo:
                CodigoAutenticacaoLog.objects.create(
                    codigo=codigo,
                    usuario=request.user,
                    acao=CodigoAutenticacaoLog.Acao.VALIDACAO,
                    ip=ip,
                    user_agent=user_agent,
                )
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": _("Código validado")})
            messages.success(request, _("Código validado"))
            form = ValidarCodigoAutenticacaoForm(usuario=request.user)
            return render(
                request,
                "tokens/validar_codigo_autenticacao.html",
                {"form": form, "success": _("Código validado")},
            )
        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        codigo = getattr(form, "codigo_obj", None)
        if codigo:
            if "Código incorreto" not in form.errors.get("codigo", []):
                codigo.tentativas += 1
                codigo.save(update_fields=["tentativas"])
            CodigoAutenticacaoLog.objects.create(
                codigo=codigo,
                usuario=request.user,
                acao=CodigoAutenticacaoLog.Acao.VALIDACAO,
                ip=ip,
                user_agent=user_agent,
            )
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "tokens/_resultado.html",
                {"error": form.errors.as_text()},
                status=400,
            )
        messages.error(request, form.errors.as_text())
        return render(
            request,
            "tokens/validar_codigo_autenticacao.html",
            {"form": form, "error": form.errors.as_text()},
            status=400,
        )


class Ativar2FAView(LoginRequiredMixin, View):
    template_name = "tokens/ativar_2fa.html"

    def _get_qr_code(self, user):
        otp_uri = pyotp.totp.TOTP(user.two_factor_secret).provisioning_uri(name=user.email, issuer_name="Hubx")
        img = qrcode.make(otp_uri)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.two_factor_enabled:
            messages.info(request, _("2FA já está habilitado."))
            return redirect("accounts:seguranca")
        if not user.two_factor_secret:
            user.two_factor_secret = pyotp.random_base32()
            user.save(update_fields=["two_factor_secret"])
        context = {
            "form": Ativar2FAForm(),
            "qr_code": self._get_qr_code(user),
            "secret": user.two_factor_secret,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = request.user
        form = Ativar2FAForm(request.POST, user=user)
        if form.is_valid():
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_enabled"])
            TOTPDevice.all_objects.update_or_create(
                usuario=user,
                defaults={
                    "secret": user.two_factor_secret,
                    "confirmado": True,
                    "deleted": False,
                    "deleted_at": None,
                },
            )
            SecurityEvent.objects.create(
                usuario=user,
                evento="2fa_habilitado",
                ip=get_client_ip(request),
            )
            messages.success(request, _("2FA ativado"))
            return redirect("accounts:seguranca")
        context = {
            "form": form,
            "qr_code": self._get_qr_code(user),
            "secret": user.two_factor_secret,
        }
        return render(request, self.template_name, context)


class Desativar2FAView(LoginRequiredMixin, View):
    template_name = "tokens/desativar_2fa.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        user = request.user
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.save(update_fields=["two_factor_enabled", "two_factor_secret"])
        TOTPDevice.objects.filter(usuario=user).delete()
        SecurityEvent.objects.create(
            usuario=user,
            evento="2fa_desabilitado",
            ip=get_client_ip(request),
        )
        messages.success(request, _("2FA desativado"))
        return redirect("accounts:seguranca")
