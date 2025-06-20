from django.shortcuts import render, redirect


def home(request):
    if request.user.is_authenticated:
        return redirect('accounts:perfil')
    return render(request, 'core/home.html')
