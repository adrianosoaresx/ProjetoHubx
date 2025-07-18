from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.http import JsonResponse

from .forms import TokenAcessoForm
from .models import TokenAcesso, CodigoAutenticacao, TOTPDevice

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
    if request.user.tipo_id not in {User.Tipo.SUPERADMIN, User.Tipo.ADMIN}:
        return redirect("accounts:perfil")

    token = None
    if request.method == "POST":
        form = TokenAcessoForm(request.POST, user=request.user)
        if form.is_valid():
            token = form.save(commit=False)
            token.gerado_por = request.user
            token.save()
    else:
        form = TokenAcessoForm(user=request.user)

    return render(
        request,
        "tokens/gerar_token.html",
        {"form": form, "token": token},
    )


class GerarTokenConviteView(View):
    def post(self, request):
        # TODO: Implementar lógica para gerar token de convite
        pass


class ValidarTokenConviteView(View):
    def post(self, request):
        # TODO: Implementar lógica para validar token de convite
        pass


class GerarCodigoAutenticacaoView(View):
    def post(self, request):
        # TODO: Implementar lógica para gerar código de autenticação
        pass


class ValidarCodigoAutenticacaoView(View):
    def post(self, request):
        # TODO: Implementar lógica para validar código de autenticação
        pass


class Ativar2FAView(View):
    def post(self, request):
        # TODO: Implementar lógica para ativar 2FA
        pass
