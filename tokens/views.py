from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

from .forms import (
    Ativar2FAForm,
    GerarCodigoAutenticacaoForm,
    GerarTokenConviteForm,
    TokenAcessoForm,
    ValidarCodigoAutenticacaoForm,
    ValidarTokenConviteForm,
)
from .models import TokenAcesso, TOTPDevice

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
            token = form.save(commit=False)
            token.gerado_por = request.user
            token.save()
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


class GerarTokenConviteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"error": _("Não autorizado")}, status=403)
            return JsonResponse({"error": _("Não autorizado")}, status=403)
        form = GerarTokenConviteForm(request.POST, user=request.user)
        if form.is_valid():
            token = TokenAcesso(
                tipo_destino=form.cleaned_data["tipo_destino"],
                organizacao=form.cleaned_data.get("organizacao"),
                gerado_por=request.user,
                data_expiracao=timezone.now() + timezone.timedelta(days=30),
            )
            token.save()
            token.nucleos.set(form.cleaned_data["nucleos"])
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"token": token.codigo})
            messages.success(request, _("Token gerado"))
            return JsonResponse({"codigo": token.codigo})
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
            token.save()
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
    def post(self, request, *args, **kwargs):
        device, created = TOTPDevice.objects.get_or_create(usuario=request.user)
        form = Ativar2FAForm(request.POST, device=device)
        if form.is_valid():
            device.confirmado = True
            device.save()
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": _("2FA ativado")})
            messages.success(request, _("2FA ativado"))
            return JsonResponse({"success": _("2FA ativado")})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": form.errors.as_text()}, status=400)
        messages.error(request, form.errors.as_text())
        return JsonResponse({"error": form.errors.as_text()}, status=400)


class Desativar2FAView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        TOTPDevice.objects.filter(usuario=request.user).delete()
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"success": _("2FA desativado")})
        messages.success(request, _("2FA desativado"))
        return JsonResponse({"success": _("2FA desativado")})
