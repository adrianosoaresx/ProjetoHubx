from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
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
        else:
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "tokens/_resultado.html",
                    {"error": form.errors.as_text()},
                    status=400,
                )
    else:
        form = TokenAcessoForm()

    return render(
        request,
        "tokens/gerar_token.html",
        {"form": form, "token": token},
    )


class GerarTokenConviteView(View):
    def post(self, request, *args, **kwargs):
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
            return JsonResponse({"codigo": token.codigo})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": "Dados inválidos"}, status=400)
        return JsonResponse({"error": "Dados inválidos"}, status=400)


class ValidarTokenConviteView(View):
    def post(self, request, *args, **kwargs):
        form = ValidarTokenConviteForm(request.POST)
        if form.is_valid():
            token = form.token
            token.usuario = request.user
            token.estado = TokenAcesso.Estado.USADO
            token.save()
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": "Token validado"})
            return JsonResponse({"success": "Token validado"})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": form.errors.as_text()}, status=400)
        return JsonResponse({"error": form.errors.as_text()}, status=400)


class GerarCodigoAutenticacaoView(View):
    def post(self, request, *args, **kwargs):
        form = GerarCodigoAutenticacaoForm(request.POST)
        if form.is_valid():
            codigo = form.save()
            # TODO: enviar via email/SMS
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"codigo": codigo.codigo})
            return JsonResponse({"codigo": codigo.codigo})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": "Dados inválidos"}, status=400)
        return JsonResponse({"error": "Dados inválidos"}, status=400)


class ValidarCodigoAutenticacaoView(View):
    def post(self, request, *args, **kwargs):
        form = ValidarCodigoAutenticacaoForm(request.POST, usuario=request.user)
        if form.is_valid():
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": "Código validado"})
            return JsonResponse({"success": "Código validado"})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": form.errors.as_text()}, status=400)
        return JsonResponse({"error": form.errors.as_text()}, status=400)


class Ativar2FAView(View):
    def post(self, request, *args, **kwargs):
        device, _ = TOTPDevice.objects.get_or_create(usuario=request.user)
        form = Ativar2FAForm(request.POST, device=device)
        if form.is_valid():
            device.confirmado = True
            device.save()
            if request.headers.get("HX-Request") == "true":
                return render(request, "tokens/_resultado.html", {"success": "2FA ativado"})
            return JsonResponse({"success": "2FA ativado"})
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"error": form.errors.as_text()}, status=400)
        return JsonResponse({"error": form.errors.as_text()}, status=400)


class Desativar2FAView(View):
    def post(self, request, *args, **kwargs):
        TOTPDevice.objects.filter(usuario=request.user).delete()
        if request.headers.get("HX-Request") == "true":
            return render(request, "tokens/_resultado.html", {"success": "2FA desativado"})
        return JsonResponse({"success": "2FA desativado"})
