from django.shortcuts import render
from django.http import HttpResponse

def login_view(request):
    return render(request, 'login/login.html')

def password_reset(request):
    return render(request, 'login/login.html')

def onboarding(request):
    return render(request, 'register/onboarding.html')

def nome(request):
    return render(request, 'register/nome.html')

def email(request):
    return render(request, 'register/email.html')

def token(request):
    if request.method == "POST":
        token_value = request.POST.get('token')
        if token_value:  # validações aqui
            request.session['invite_token'] = token_value
            return redirect('custom_auth:nome')
        
    return render(request, 'register/token.html')

def usuario(request):
    return render(request, 'register/usuario.html')

def senha(request):
    return render(request, 'register/senha.html')

def foto(request):
    return render(request, 'register/foto.html')

def termos(request):
    return render(request, 'register/termos.html')