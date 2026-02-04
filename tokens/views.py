from __future__ import annotations

import base64
from io import BytesIO

import pyotp
import qrcode
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

from accounts.models import SecurityEvent, UserType
from audit.models import AuditLog
from audit.services import hash_ip, log_audit
from notificacoes.services.email_client import send_email
from notificacoes.services.whatsapp_client import send_whatsapp

from core.utils import resolve_back_href
from eventos.models import Evento

from .forms import (
    Ativar2FAForm,
    GerarCodigoAutenticacaoForm,
    GerarTokenConviteForm,
    ValidarCodigoAutenticacaoForm,
    ValidarTokenConviteForm,
)
from .metrics import (
    tokens_invites_created_total,
    tokens_rate_limited_total,
)
from .models import CodigoAutenticacaoLog, TokenAcesso, TokenUsoLog, TOTPDevice
from .perms import can_issue_invite
from .ratelimit import check_rate_limit
from .services import create_invite_token, invite_created
from .utils import get_client_ip

User = get_user_model()

ROOT_TOKENS_FORBIDDEN_MESSAGE = _("Usuários root não gerenciam tokens de acesso.")
AUTH_RENDER_CONTEXT = {"hide_nav": True}


def _redirect_root_from_tokens(request):
    user_type = getattr(request.user, "get_tipo_usuario", None)
    if user_type == UserType.ROOT.value:
        messages.error(request, ROOT_TOKENS_FORBIDDEN_MESSAGE)
        return redirect("organizacoes:list")
    return None


def _get_query_param(request, key: str):
    """Recupera um parâmetro da query string, incluindo variantes com ``amp;``.

    Alguns provedores de e-mail podem escapar os separadores de query string e
    enviar links contendo ``amp;`` no lugar do ``&``. Ao abrir o link, o
    navegador interpreta ``amp;token`` como o nome do parâmetro, o que faz com
    que ``request.GET.get("token")`` retorne ``None``. Este helper cobre esse
    cenário mantendo compatibilidade com o parâmetro correto.
    """

    return request.GET.get(key) or request.GET.get(f"amp;{key}")


def token(request):
    raw_event_id = _get_query_param(request, "evento") or request.session.get("invite_event_id")
    evento = None
    if raw_event_id:
        try:
            evento = Evento.objects.select_related("organizacao").get(pk=raw_event_id)
            request.session["invite_event_id"] = str(evento.pk)
        except (Evento.DoesNotExist, ValueError):
            request.session.pop("invite_event_id", None)

    if request.user.is_authenticated:
        redirect_response = _redirect_root_from_tokens(request)
        if redirect_response:
            return redirect_response
        if request.user.is_superuser or request.user.get_tipo_usuario == UserType.ADMIN.value:
            return redirect("tokens:listar_convites")

    def _handle_token_success(token_obj, token_code):
        if evento and token_obj.organizacao_id and evento.organizacao_id != token_obj.organizacao_id:
            messages.error(request, _("Convite não corresponde ao evento informado."))
            return redirect("tokens:token")

        if evento:
            request.session["invite_event_id"] = str(evento.pk)
            if evento.publico_alvo != 0:
                messages.error(request, _("O evento não está disponível para o público geral."))
                return redirect("tokens:token")

        request.session["invite_token"] = token_code
        return redirect("accounts:usuario")

    prefilled_email = _get_query_param(request, "email")
    if prefilled_email:
        request.session["email"] = prefilled_email
        request.session["invite_email"] = prefilled_email

    prefilled_token = _get_query_param(request, "token")
    if prefilled_token:
        prefill_form = ValidarTokenConviteForm({"token": prefilled_token})
        if prefill_form.is_valid():
            token_obj = prefill_form.token
            response = _handle_token_success(token_obj, prefilled_token)
            if response:
                return response
        else:
            messages.error(request, _("Token inválido."))

    initial_token = prefilled_token or request.session.get("invite_token")

    form = (
        ValidarTokenConviteForm(initial={"token": initial_token})
        if initial_token
        else ValidarTokenConviteForm()
    )
    if request.method == "POST":
        form = ValidarTokenConviteForm(request.POST)
        if form.is_valid():
            tkn = form.cleaned_data["token"]
            token_obj = form.token
            response = _handle_token_success(token_obj, tkn)
            if response:
                return response
    return render(
        request,
        "register/token.html",
        {"form": form, **AUTH_RENDER_CONTEXT},
    )


@login_required
def listar_convites(request):
    redirect_response = _redirect_root_from_tokens(request)
    if redirect_response:
        return redirect_response
    if not request.user.is_staff:
        messages.error(request, _("Você não tem permissão para visualizar convites."))
        return redirect("accounts:perfil")
    convites_qs = TokenAcesso.objects.filter(gerado_por=request.user)

    totais = {
        "total": convites_qs.count(),
        "novos": convites_qs.filter(estado=TokenAcesso.Estado.NOVO).count(),
        "usados": convites_qs.filter(estado=TokenAcesso.Estado.USADO).count(),
        "expirados": convites_qs.filter(estado=TokenAcesso.Estado.EXPIRADO).count(),
        "revogados": convites_qs.filter(estado=TokenAcesso.Estado.REVOGADO).count(),
    }

    convites = []
    for convite in convites_qs:
        preview = convite.codigo_preview or convite.codigo_hash[:8]
        convite.preview_display = preview
        convites.append(convite)

    fallback_url = reverse("feed:meu_mural")
    back_href = resolve_back_href(request, fallback=fallback_url)
    navigation_context = {
        "back_href": back_href,
        "back_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
    }

    context = {"convites": convites, "totais": totais, **navigation_context}
    return render(request, "tokens/token_list.html", context)





class GerarTokenConviteView(LoginRequiredMixin, View):
    def _navigation_context(self, request):
        fallback_url = reverse("tokens:listar_convites")
        back_href = resolve_back_href(request, fallback=fallback_url)
        return {
            "back_href": back_href,
            "back_component_config": {
                "href": back_href,
                "fallback_href": fallback_url,
            },
            "cancel_component_config": {
                "href": back_href,
                "fallback_href": fallback_url,
            },
        }

    def get(self, request, *args, **kwargs):
        redirect_response = _redirect_root_from_tokens(request)
        if redirect_response:
            return redirect_response
        form = GerarTokenConviteForm(user=request.user)
        if not form.fields["tipo_destino"].choices:
            messages.error(
                request,
                _("Seu perfil não permite gerar convites."),
            )
            return redirect("accounts:perfil")
        if not getattr(request.user, "organizacao", None):
            messages.error(
                request,
                _("Seu usuário não está associado a nenhuma organização."),
            )
            return redirect("accounts:perfil")
        context = {"form": form, **self._navigation_context(request)}
        return render(request, "tokens/gerar_token.html", context)

    def post(self, request, *args, **kwargs):
        redirect_response = _redirect_root_from_tokens(request)
        if redirect_response:
            return redirect_response
        ip = get_client_ip(request)
        rl = check_rate_limit(f"user:{request.user.id}:{ip}")
        if not rl.allowed:
            tokens_rate_limited_total.inc()
            log_audit(
                request.user,
                "token_invite_rate_limited",
                object_type="TokenAcesso",
                ip_hash=hash_ip(ip),
                status=AuditLog.Status.FAILURE,
            )
            if request.headers.get("HX-Request") == "true":
                resp = render(
                    request,
                    "tokens/_resultado.html",
                    {"error": _("Muitas requisições, tente novamente mais tarde.")},
                    status=429,
                )
            else:
                messages.error(request, _("Muitas requisições, tente novamente mais tarde."))
                form = GerarTokenConviteForm(user=request.user)
                resp = render(
                    request,
                    "tokens/gerar_token.html",
                    {
                        "form": form,
                        **self._navigation_context(request),
                    },
                    status=429,
                )
            if rl.retry_after:
                resp["Retry-After"] = str(rl.retry_after)
            return resp
        form = GerarTokenConviteForm(request.POST, user=request.user)
        organizacao = getattr(request.user, "organizacao", None)
        if not organizacao:
            message = _("Seu usuário não está associado a nenhuma organização.")
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "tokens/_resultado.html",
                    {"error": message},
                    status=400,
                )
            messages.error(request, message)
            return render(
                request,
                "tokens/gerar_token.html",
                {
                    "form": form,
                    "error": message,
                    **self._navigation_context(request),
                },
                status=400,
            )
        target_role_value = TokenAcesso.TipoUsuario.CONVIDADO.value
        requested_role = request.POST.get("tipo_destino")
        if requested_role and requested_role != target_role_value:
            message = _("Somente convites para convidados estão disponíveis.")
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "tokens/_resultado.html",
                    {"error": message},
                    status=400,
                )
            messages.error(request, message)
            return render(
                request,
                "tokens/gerar_token.html",
                {
                    "form": form,
                    "error": message,
                    **self._navigation_context(request),
                },
                status=400,
            )

        if not can_issue_invite(request.user, target_role_value):
            message = _("Seu perfil não permite gerar convites.")
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "tokens/_resultado.html",
                    {"error": message},
                    status=403,
                )
            messages.error(request, message)
            return render(
                request,
                "tokens/gerar_token.html",
                {
                    "form": form,
                    "error": message,
                    **self._navigation_context(request),
                },
                status=403,
            )
        if form.is_valid():
            target_role = target_role_value

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
                    {
                        "form": form,
                        "error": _("Limite diário atingido."),
                        **self._navigation_context(request),
                    },
                    status=429,
                )

            token, codigo = create_invite_token(
                gerado_por=request.user,
                tipo_destino=target_role,
                data_expiracao=timezone.now() + timezone.timedelta(days=30),
                organizacao=request.user.organizacao,
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
            invite_created(token, codigo)
            tokens_invites_created_total.inc()
            token.codigo = codigo

            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"token": codigo})
            messages.success(request, _("Token gerado"))
            form = GerarTokenConviteForm(user=request.user)
            return render(
                request,
                "tokens/gerar_token.html",
                {
                    "form": form,
                    "token": codigo,
                    **self._navigation_context(request),
                },
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
            {
                "form": form,
                "error": _("Dados inválidos"),
                **self._navigation_context(request),
            },
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
    template_name = "configuracoes/seguranca/ativar_2fa.html"

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
            return redirect("configuracoes:configuracoes")
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
            return redirect("configuracoes:configuracoes")
        SecurityEvent.objects.create(
            usuario=user,
            evento="2fa_habilitacao_falha",
            ip=get_client_ip(request),
        )
        context = {
            "form": form,
            "qr_code": self._get_qr_code(user),
            "secret": user.two_factor_secret,
        }
        return render(request, self.template_name, context)


class Desativar2FAView(LoginRequiredMixin, View):
    template_name = "configuracoes/seguranca/desativar_2fa.html"

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
        return redirect("configuracoes:configuracoes")
