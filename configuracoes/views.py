from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.generic import View

from accounts.forms import InformacoesPessoaisForm, RedesSociaisForm
from notificacoes.forms import UserNotificationPreferenceForm
from notificacoes.models import UserNotificationPreference
from tokens.models import TOTPDevice


class ConfiguracoesView(LoginRequiredMixin, View):
    """Exibe e processa formulários de configuração da conta."""

    form_classes = {
        "informacoes": InformacoesPessoaisForm,
        "seguranca": PasswordChangeForm,
        "redes": RedesSociaisForm,
        "notificacoes": UserNotificationPreferenceForm,
    }

    def get_form(self, tab: str, data=None, files=None):
        user = self.request.user
        form_class = self.form_classes[tab]
        if form_class is PasswordChangeForm:
            return form_class(user, data)
        if form_class is UserNotificationPreferenceForm:
            pref, _ = UserNotificationPreference.objects.get_or_create(user=user)
            return form_class(data, instance=pref)
        return form_class(data, files, instance=user)

    def get_two_factor_enabled(self) -> bool:
        return TOTPDevice.objects.filter(usuario=self.request.user, confirmado=True).exists()

    def get(self, request):
        tab = request.GET.get("tab", "informacoes")
        context = {f"{name}_form": self.get_form(name) for name in self.form_classes}
        context.update(
            {
                "tab": tab,
                "two_factor_enabled": self.get_two_factor_enabled(),
                "redes_conectadas": request.user.redes_sociais or {},
            }
        )
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
                saved = form.save()
                if isinstance(form, PasswordChangeForm):
                    update_session_auth_hash(request, saved)
                messages.success(request, _("Alterações salvas com sucesso."))
            else:
                messages.error(request, _("Corrija os erros abaixo."))

        context = {f"{name}_form": form if name == tab else self.get_form(name) for name in self.form_classes}
        context.update(
            {
                "tab": tab,
                "two_factor_enabled": self.get_two_factor_enabled(),
                "redes_conectadas": request.user.redes_sociais or {},
            }
        )
        template = (
            f"configuracoes/partials/{tab}.html"
            if request.headers.get("HX-Request")
            else "configuracoes/configuracoes.html"
        )
        return render(request, template, context)
