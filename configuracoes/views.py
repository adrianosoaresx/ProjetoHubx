from typing import Any

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AbstractBaseUser
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from accounts.models import AccountToken, SecurityEvent
from configuracoes.forms import ConfiguracaoContaForm
from configuracoes.services import atualizar_preferencias_usuario, get_configuracao_conta
from tokens.utils import get_client_ip


class ConfiguracoesView(LoginRequiredMixin, View):
    """Exibe e processa formulários de configuração da conta."""

    form_classes = {
        "seguranca": PasswordChangeForm,
        "preferencias": ConfiguracaoContaForm,
    }

    def get_user(self) -> AbstractBaseUser:
        if not hasattr(self, "_user_cache"):
            User = get_user_model()
            self._user_cache = User.objects.select_related("configuracao").get(pk=self.request.user.pk)
        return self._user_cache

    def get_form(self, tab: str | None, data: dict[str, Any] | None = None, files: Any | None = None) -> forms.Form:
        tab = tab or "seguranca"
        if tab not in self.form_classes:
            raise Http404
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

    def get(self, request: HttpRequest) -> HttpResponse:
        tab = request.GET.get("tab", "seguranca")
        if tab == "informacoes":
            return redirect("accounts:informacoes_pessoais")
        if tab == "redes":
            return redirect("accounts:redes_sociais")
        context = {
            f"{tab}_form": self.get_form(tab),
            "tab": tab,
            "two_factor_enabled": self.get_two_factor_enabled(),
        }
        template = (
            f"configuracoes/_partials/{tab}.html"
            if request.headers.get("HX-Request")
            else "configuracoes/configuracoes.html"
        )
        return render(request, template, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        tab = request.GET.get("tab") or request.POST.get("tab")
        tab = tab or "seguranca"
        if tab == "informacoes":
            return redirect("accounts:informacoes_pessoais")
        if tab == "redes":
            return redirect("accounts:redes_sociais")
        if tab not in self.form_classes:
            raise Http404
        form = self.get_form(tab, request.POST, request.FILES)
        if form.is_valid():
            if tab == "preferencias":
                form.instance = atualizar_preferencias_usuario(request.user, form.cleaned_data)
            else:
                saved = form.save()
                if isinstance(form, PasswordChangeForm):
                    AccountToken.objects.filter(
                        usuario=request.user,
                        tipo=AccountToken.Tipo.PASSWORD_RESET,
                        used_at__isnull=True,
                    ).update(used_at=timezone.now())
                    update_session_auth_hash(request, saved)
                    SecurityEvent.objects.create(
                        usuario=request.user,
                        evento="senha_alterada",
                        ip=get_client_ip(request),
                    )
            messages.success(request, _("Alterações salvas com sucesso."))
        else:
            messages.error(request, _("Corrija os erros abaixo."))

        context = {
            f"{tab}_form": form,
            "tab": tab,
            "two_factor_enabled": self.get_two_factor_enabled(),
        }
        if tab == "preferencias" and form.is_valid():
            context["updated_preferences"] = True
        template = (
            f"configuracoes/_partials/{tab}.html"
            if request.headers.get("HX-Request")
            else "configuracoes/configuracoes.html"
        )
        response = render(request, template, context)
        if tab == "preferencias" and form.is_valid():
            tema = form.instance.tema
            response.set_cookie(
                "tema",
                tema,
                httponly=False,
                secure=request.is_secure(),
                samesite="Lax",
            )
            response.set_cookie(
                "django_language",
                form.instance.idioma,
                httponly=False,
                secure=request.is_secure(),
                samesite="Lax",
            )
        return response
