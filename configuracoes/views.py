from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from configuracoes.forms import ConfiguracaoContaForm

class ConfiguracoesView(LoginRequiredMixin, View):
    def get(self, request):
        form = ConfiguracaoContaForm(instance=request.user.configuracao)
        return render(request, "configuracoes/configuracoes.html", {"form": form})

    def post(self, request):
        form = ConfiguracaoContaForm(request.POST, instance=request.user.configuracao)
        if form.is_valid():
            form.save()
            return render(request, "configuracoes/configuracoes.html", {"form": form, "success": True})
        return render(request, "configuracoes/configuracoes.html", {"form": form})
