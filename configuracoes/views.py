from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.generic import View

from accounts.forms import InformacoesPessoaisForm, RedesSociaisForm
from configuracoes.forms import ConfiguracaoContaForm
from configuracoes.services import atualizar_preferencias_usuario, get_configuracao_conta


class ConfiguracoesView(LoginRequiredMixin, View):
    """Exibe e processa formulários de configuração da conta."""

    form_classes = {
        "informacoes": InformacoesPessoaisForm,
        "seguranca": PasswordChangeForm,
        "redes": RedesSociaisForm,
        "preferencias": ConfiguracaoContaForm,
    }

    def get_user(self):
        if not hasattr(self, "_user_cache"):
            User = get_user_model()
            self._user_cache = User.objects.select_related("configuracao").get(pk=self.request.user.pk)
        return self._user_cache

    def get_form(self, tab: str, data=None, files=None):
        user = self.get_user()
        form_class = self.form_classes[tab]
        if form_class is PasswordChangeForm:
            return form_class(user, data)
        if form_class is ConfiguracaoContaForm:
            return form_class(data, instance=get_configuracao_conta(user))
        return form_class(data, files, instance=user)

    def get_two_factor_enabled(self) -> bool:
        """Retorna se o usuário atual possui 2FA habilitado."""
        return bool(self.request.user.two_factor_enabled)

    def get(self, request):
        tab = request.GET.get("tab", "informacoes")
        context = {
            f"{tab}_form": self.get_form(tab),
            "tab": tab,
            "two_factor_enabled": self.get_two_factor_enabled(),
            "redes_conectadas": request.user.redes_sociais or {},
        }
        template = (
            f"configuracoes/partials/{tab}.html"
            if request.headers.get("HX-Request")
            else "configuracoes/configuracoes.html"
        )
        return render(request, template, context)

    def post(self, request):
        tab = request.GET.get("tab", request.POST.get("tab", "informacoes"))
        if tab == "redes" and request.POST.get("action") == "disconnect":
            redes = request.user.redes_sociais or {}
            network = request.POST.get("network")
            if network in redes:
                redes.pop(network)
                request.user.redes_sociais = redes
                request.user.save()
                messages.success(request, _("Conta desconectada."))
            else:
                messages.error(request, _("Rede social não encontrada."))
            form = self.get_form("redes")
        else:
            form = self.get_form(tab, request.POST, request.FILES)
            if form.is_valid():
                if tab == "preferencias":
                    form.instance = atualizar_preferencias_usuario(request.user, form.cleaned_data)
                else:
                    saved = form.save()
                    if isinstance(form, PasswordChangeForm):
                        update_session_auth_hash(request, saved)
                messages.success(request, _("Alterações salvas com sucesso."))
            else:
                messages.error(request, _("Corrija os erros abaixo."))

        context = {
            f"{tab}_form": form,
            "tab": tab,
            "two_factor_enabled": self.get_two_factor_enabled(),
            "redes_conectadas": request.user.redes_sociais or {},
        }
        if tab == "preferencias" and form.is_valid():
            context["updated_preferences"] = True
        template = (
            f"configuracoes/partials/{tab}.html"
            if request.headers.get("HX-Request")
            else "configuracoes/configuracoes.html"
        )
        response = render(request, template, context)
        if tab == "preferencias" and form.is_valid():
            tema = form.instance.tema
            response.set_cookie("tema", tema)
            response.set_cookie("django_language", form.instance.idioma)
        return response
