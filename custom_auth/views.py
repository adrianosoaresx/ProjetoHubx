from django.shortcuts import render, redirect
from django.http import HttpResponse

def login_view(request):
    return render(request, 'login/login.html')

def password_reset(request):
    return render(request, 'login/login.html')

def onboarding(request):
    return render(request, 'register/onboarding.html')

def nome(request):
    if request.method == "POST":
        nome_value = request.POST.get('nome')
        if nome_value:
            request.session['nome'] = nome_value
            return redirect('custom_auth:email')
    return render(request, 'register/nome.html')

def email(request):
    if request.method == "POST":
        email_value = request.POST.get('email')
        if email_value:
            request.session['email'] = email_value
            return redirect('custom_auth:senha')
    return render(request, 'register/email.html')

def token(request):
    if request.method == "POST":
        token_value = request.POST.get('token')
        if token_value:  # validações aqui
            request.session['invite_token'] = token_value
            return redirect('custom_auth:usuario')

    return render(request, 'register/token.html')

def usuario(request):
    if request.method == "POST":
        usuario_value = request.POST.get('usuario')
        if usuario_value:
            request.session['usuario'] = usuario_value
            return redirect('custom_auth:nome')
    return render(request, 'register/usuario.html')

def senha(request):
    if request.method == "POST":
        senha1 = request.POST.get('senha1')
        senha2 = request.POST.get('senha2')
        if senha1 and senha1 == senha2:
            request.session['senha'] = senha1
            return redirect('custom_auth:foto')
    return render(request, 'register/senha.html')

def foto(request):
    if request.method == "POST":
        foto_file = request.FILES.get('foto')
        if foto_file:
            request.session['foto'] = foto_file.name
        return redirect('custom_auth:termos')
    return render(request, 'register/foto.html')

def termos(request):
    if request.method == "POST":
        if request.POST.get("aceitar_termos"):
            request.session["termos"] = True
            return redirect("registro_sucesso")
    return render(request, "register/termos.html")

def registro_sucesso(request):
    return render(request, 'register/registro_sucesso.html')
