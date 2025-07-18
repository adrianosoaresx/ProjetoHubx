from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.http import JsonResponse

from .forms import TokenAcessoForm, GerarTokenConviteForm
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
    def post(self, request, *args, **kwargs):
        form = GerarTokenConviteForm(request.POST, user=request.user)
        if form.is_valid():
            token = TokenAcesso(
                tipo_destino=form.cleaned_data["tipo_destino"],
                organizacao=form.cleaned_data["organizacao"],
                gerado_por=request.user,
                data_expiracao=timezone.now() + timezone.timedelta(days=30),
            )
            token.save()
            token.nucleos.set(form.cleaned_data["nucleos"])
            return JsonResponse({"codigo": token.codigo})
        return JsonResponse({"error": "Dados inválidos"}, status=400)


class ValidarTokenConviteView(View):
    def post(self, request, *args, **kwargs):
        codigo = request.POST.get("codigo")
        try:
            token = TokenAcesso.objects.get(codigo=codigo, estado="novo")
            if token.data_expiracao < timezone.now():
                return JsonResponse({"error": "Token expirado"}, status=400)

            token.estado = "usado"
            token.usuario_associado = request.user
            token.save()
            return JsonResponse({"success": "Token validado com sucesso"})
        except TokenAcesso.DoesNotExist:
            return JsonResponse({"error": "Token inválido"}, status=400)


class GerarCodigoAutenticacaoView(View):
    def post(self, request, *args, **kwargs):
        usuario_alvo = User.objects.get(id=request.POST.get("usuario_id"))
        codigo = CodigoAutenticacao.objects.create(
            usuario=usuario_alvo,
            codigo=CodigoAutenticacao.gerar_codigo(),
            data_expiracao=timezone.now() + timezone.timedelta(minutes=10),
        )
        # TODO: Implementar envio de código via e-mail/SMS
        return JsonResponse({"success": "Código gerado e enviado"})


class ValidarCodigoAutenticacaoView(View):
    def post(self, request, *args, **kwargs):
        codigo = request.POST.get("codigo")
        try:
            autenticacao = CodigoAutenticacao.objects.get(codigo=codigo, verificado=False)
            if autenticacao.data_expiracao < timezone.now():
                return JsonResponse({"error": "Código expirado"}, status=400)

            autenticacao.verificado = True
            autenticacao.save()
            return JsonResponse({"success": "Código validado com sucesso"})
        except CodigoAutenticacao.DoesNotExist:
            return JsonResponse({"error": "Código inválido"}, status=400)


class Ativar2FAView(View):
    def post(self, request, *args, **kwargs):
        totp_device = TOTPDevice.objects.create(
            usuario=request.user,
            segredo=TOTPDevice.gerar_segredo(),
        )
        codigo_totp = request.POST.get('codigo_totp')
        if not totp_device.validar_codigo(codigo_totp):
            return JsonResponse({'error': 'Código TOTP inválido'}, status=400)

        totp_device.ativo = True
        totp_device.save()
        return JsonResponse({'success': '2FA ativado com sucesso'})
