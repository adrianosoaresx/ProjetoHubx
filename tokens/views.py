from __future__ import annotations

import base64
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

from . import services
from .forms import (
    Ativar2FAForm,
    GerarCodigoAutenticacaoForm,
    GerarTokenConviteForm,
    TokenAcessoForm,
    ValidarCodigoAutenticacaoForm,
    ValidarTokenConviteForm,
)
from .metrics import tokens_invites_revoked_total
from .models import ApiToken, ApiTokenLog, TokenAcesso, TokenUsoLog, TOTPDevice
from .perms import can_issue_invite
from .services import create_invite_token

User = get_user_model()


def token(request):
    if request.method == "POST":
        tkn = request.POST.get("token")
        if tkn:
            request.session["invite_token"] = tkn
            return redirect("accounts:usuario")
    return render(request, "register/token.html")


@login_required
def criar_token(request):
    if not request.user.is_staff:
        messages.error(request, _("Você não tem permissão para gerar tokens."))
        return redirect("accounts:perfil")

    token = None
    if request.method == "POST":
        form = TokenAcessoForm(request.POST)
        if form.is_valid():
            token, codigo = create_invite_token(
                gerado_por=request.user,
                tipo_destino=form.cleaned_data["tipo_destino"],
            )
            ip = request.META.get("REMOTE_ADDR", "")
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
                return render(request, "tokens/_resultado.html", {"token": token.codigo})
            messages.success(request, _("Token gerado"))
        else:
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "tokens/_resultado.html",
                    {"error": form.errors.as_text()},
                    status=400,
                )
            messages.error(request, _("Dados inválidos"))
    else:
        form = TokenAcessoForm()

    return render(
        request,
        "tokens/gerar_token.html",
        {"form": form, "token": token},
    )


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
            ip=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        tokens_invites_revoked_total.inc()
        messages.success(request, _("Convite revogado."))
    else:
        messages.info(request, _("Convite já estava revogado."))
    return redirect("tokens:listar_convites")


@login_required
def listar_api_tokens(request):
    tokens = services.list_tokens(request.user)
    return render(request, "tokens/api_tokens.html", {"tokens": tokens})


@login_required
def revogar_api_token(request, token_id: str):
    token = get_object_or_404(ApiToken, id=token_id, user=request.user)
    if token.revoked_at:
        messages.info(request, _("Token já revogado."))
    else:
        services.revoke_token(token.id, revogado_por=request.user)
        ApiTokenLog.objects.create(
            token=token,
            usuario=request.user,
            acao=ApiTokenLog.Acao.REVOGACAO,
            ip=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        messages.success(request, _("Token revogado."))
    return redirect("tokens:listar_api_tokens")


class GerarTokenConviteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"error": _("Não autorizado")}, status=403)
            return JsonResponse({"error": _("Não autorizado")}, status=403)
        form = GerarTokenConviteForm(request.POST, user=request.user)
        if form.is_valid():

            token, codigo = create_invite_token(gerado_por=request.user, tipo_destino=form.cleaned_data["tipo_destino"])

            target_role = form.cleaned_data["tipo_destino"]
            if not can_issue_invite(request.user, target_role):
                if request.headers.get("HX-Request") == "true":
                    return render(
                        request,
                        "tokens/_resultado.html",
                        {"error": _("Não autorizado")},
                        status=403,
                    )
                return JsonResponse({"error": _("Não autorizado")}, status=403)

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
                        status=409,
                    )
                messages.error(request, _("Limite diário atingido."))
                return JsonResponse({"error": _("Limite diário atingido.")}, status=409)

            token, codigo = create_invite_token(
                gerado_por=request.user,
                tipo_destino=target_role,
                data_expiracao=timezone.now() + timezone.timedelta(days=30),
                organizacao=form.cleaned_data.get("organizacao"),
                nucleos=form.cleaned_data["nucleos"],
            )

            ip = request.META.get("REMOTE_ADDR", "")
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
            return JsonResponse({"codigo": codigo})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": _("Dados inválidos")}, status=400)
        messages.error(request, _("Dados inválidos"))
        return JsonResponse({"error": _("Dados inválidos")}, status=400)


class ValidarTokenConviteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ValidarTokenConviteForm(request.POST)
        if form.is_valid():
            token = form.token
            token.usuario = request.user
            token.estado = TokenAcesso.Estado.USADO
            ip = request.META.get("REMOTE_ADDR", "")
            token.ip_utilizado = ip
            token.save(update_fields=["usuario", "estado", "ip_utilizado"])
            TokenUsoLog.objects.create(
                token=token,
                usuario=request.user,
                acao=TokenUsoLog.Acao.VALIDACAO,
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": _("Token validado")})
            messages.success(request, _("Token validado"))
            return JsonResponse({"success": _("Token validado")})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": form.errors.as_text()}, status=400)
        messages.error(request, form.errors.as_text())
        return JsonResponse({"error": form.errors.as_text()}, status=400)


class GerarCodigoAutenticacaoView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = GerarCodigoAutenticacaoForm(request.POST)
        if form.is_valid():
            codigo = form.save()
            # TODO: enviar via email/SMS
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"codigo": codigo.codigo})
            messages.success(request, _("Código gerado"))
            return JsonResponse({"codigo": codigo.codigo})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": _("Dados inválidos")}, status=400)
        messages.error(request, _("Dados inválidos"))
        return JsonResponse({"error": _("Dados inválidos")}, status=400)


class ValidarCodigoAutenticacaoView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ValidarCodigoAutenticacaoForm(request.POST, usuario=request.user)
        if form.is_valid():
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": _("Código validado")})
            messages.success(request, _("Código validado"))
            return JsonResponse({"success": _("Código validado")})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": form.errors.as_text()}, status=400)
        messages.error(request, form.errors.as_text())
        return JsonResponse({"error": form.errors.as_text()}, status=400)


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
                ip=request.META.get("REMOTE_ADDR"),
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
            ip=request.META.get("REMOTE_ADDR"),
        )
        messages.success(request, _("2FA desativado"))
        return redirect("accounts:seguranca")
