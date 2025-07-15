from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import TokenAcessoForm
from .models import TokenAcesso

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
