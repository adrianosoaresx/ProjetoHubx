from __future__ import annotations

from typing import Any, Dict

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import View

# Project‑specific imports.  These may vary depending on your actual project
# structure.  Adjust the module paths as necessary.
try:
    from configuracoes.forms import ConfiguracaoContaForm  # type: ignore
    from configuracoes.services import atualizar_preferencias_usuario, get_configuracao_conta  # type: ignore
    from accounts.models import AccountToken  # type: ignore
    from tokens.utils import get_client_ip  # type: ignore
except Exception:
    ConfiguracaoContaForm = None  # type: ignore
    def atualizar_preferencias_usuario(user, data):  # type: ignore
        return None
    def get_configuracao_conta(user):  # type: ignore
        return None
    class AccountToken:  # type: ignore
        class Tipo:
            PASSWORD_RESET = "password_reset"
        objects = None
    def get_client_ip(request: HttpRequest) -> str:  # type: ignore
        return "0.0.0.0"


def _is_htmx(request: HttpRequest) -> bool:
    """
    Determine whether the current request originates from HTMX.

    HTMX sends a header 'HX-Request: true' on AJAX requests.  Some Django
    extensions also populate request.htmx for convenience.  This helper treats any
    truthy value in either location as an HTMX request.
    """
    return bool(
        request.headers.get("HX-Request")
        or getattr(request, "htmx", False)
    )


class ConfiguracoesView(LoginRequiredMixin, View):
    """
    Exibe e processa formulários de configuração da conta.

    Esta view detecta automaticamente requisições HTMX e retorna apenas o
    fragmento (parcial) correspondente à aba ativa (``seguranca`` ou ``preferencias``),
    melhorando a performance e evitando que a página inteira (com hero e demais
    componentes) seja renderizada novamente.
    """

    # Mapeamento das abas para suas classes de formulário.
    form_classes: Dict[str, type[forms.Form]] = {
        "seguranca": PasswordChangeForm,
        "preferencias": ConfiguracaoContaForm,  # type: ignore
    }

    # Mapeamento das abas para seus templates de fragmento.
    partial_templates: Dict[str, str] = {
        "seguranca": "configuracoes/_partials/seguranca.html",
        "preferencias": "configuracoes/_partials/preferencias.html",
    }

    def get_user(self) -> Any:
        """
        Retorna o usuário atual com as relações necessárias pré-carregadas.
        Uma pequena cache local evita consultas adicionais à base de dados.
        """
        if not hasattr(self, "_user_cache"):
            User = get_user_model()
            # Seleciona relações adicionais (e.g. configuracao) para reduzir queries.
            self._user_cache = User.objects.select_related("configuracao").get(pk=self.request.user.pk)
        return self._user_cache

    def get_form(self, tab: str | None, data: Dict[str, Any] | None = None, files: Any | None = None) -> forms.Form:
        """
        Instancia o formulário correto para a aba atual.  Para a aba de segurança,
        o formulário recebe o usuário como primeiro parâmetro.  Para a aba de
        preferências, o formulário é construído a partir de uma instância de
        configuração da conta.
        """
        tab = tab or "seguranca"
        if tab not in self.form_classes:
            raise Http404
        form_class = self.form_classes[tab]
        if form_class is None:
            raise Http404("O formulário para esta aba não está disponível.")
        user = self.get_user()
        if form_class is PasswordChangeForm:
            return form_class(user, data)
        if form_class is ConfiguracaoContaForm and get_configuracao_conta is not None:
            return form_class(data, instance=get_configuracao_conta(user))  # type: ignore
        # Fallback: constrói o formulário com os dados recebidos.
        return form_class(data, files, instance=user)  # type: ignore

    def get_two_factor_enabled(self) -> bool:
        """
        Retorna se o usuário atual possui 2FA habilitado.  Algumas abas exibem
        opções relacionadas à autenticação em dois fatores.
        """
        return bool(getattr(self.request.user, "two_factor_enabled", False))

    def resolve_tab(self, request: HttpRequest) -> str:
        """
        Resolve o valor da aba a partir dos parâmetros GET ou POST.  Valores
        inválidos são normalizados para ``seguranca``.
        """
        tab = request.GET.get("tab") or request.POST.get("tab") or "seguranca"
        # Redireciona abas externas para seus respectivos módulos.
        if tab in {"informacoes", "redes"}:
            return tab
        if tab not in {"seguranca", "preferencias"}:
            raise Http404
        return tab

    def render_response(self, request: HttpRequest, tab: str, context: Dict[str, Any]) -> HttpResponse:
        """
        Renderiza a resposta apropriada para a aba, retornando um fragmento HTMX
        quando a requisição for feita via HTMX.  Adiciona o cabeçalho Vary para
        distinguir a cache entre HTMX e requests normais.
        """
        # Identifica requisição HTMX de forma robusta.
        is_htmx = _is_htmx(request)
        template = (
            self.partial_templates.get(tab, self.partial_templates["seguranca"])
            if is_htmx
            else "configuracoes/configuracao_form.html"
        )
        response = render(request, template, context)
        if is_htmx:
            # Ajusta cabeçalho Vary para que a cache (se configurada) considere o header HX-Request.
            current_vary = response.get("Vary")
            if current_vary:
                vary_headers = [h.strip() for h in current_vary.split(",") if h.strip()]
                if "HX-Request" not in vary_headers:
                    vary_headers.append("HX-Request")
                response["Vary"] = ", ".join(vary_headers)
            else:
                response["Vary"] = "HX-Request"
        return response

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Manipula requisições GET.  Para abas externas, redireciona de imediato.
        Em seguida, prepara o contexto necessário (formulário correto, aba ativa,
        status do 2FA) e delega a renderização a ``render_response``.
        """
        tab = self.resolve_tab(request)
        # Redireciona abas que pertencem a outros apps.
        if tab in {"informacoes", "redes"}:
            return redirect("accounts:perfil_sections_info")
        form = self.get_form(tab)
        context: Dict[str, Any] = {
            f"{tab}_form": form,
            "tab": tab,
            "two_factor_enabled": self.get_two_factor_enabled(),
        }
        return self.render_response(request, tab, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Manipula requisições POST.  Valida o formulário correspondente e
        persiste alterações quando possível.  Retorna sempre o fragmento HTMX em
        requisições HTMX, permitindo atualização assíncrona do conteúdo.
        """
        tab = self.resolve_tab(request)
        if tab in {"informacoes", "redes"}:
            return redirect("accounts:perfil_sections_info")
        # Instancia o formulário apropriado com os dados recebidos.
        form = self.get_form(tab, request.POST, request.FILES)
        if form.is_valid():
            # Persistir alterações conforme o tipo de formulário.
            if tab == "preferencias" and atualizar_preferencias_usuario is not None:
                form.instance = atualizar_preferencias_usuario(request.user, form.cleaned_data)  # type: ignore
            else:
                saved = form.save()
                # Quando a senha é alterada, invalidar tokens pendentes e manter o usuário autenticado.
                if isinstance(form, PasswordChangeForm) and AccountToken.objects is not None:
                    AccountToken.objects.filter(
                        usuario=request.user,
                        tipo=AccountToken.Tipo.PASSWORD_RESET,
                        used_at__isnull=True,
                    ).update(used_at=timezone.now())
                    update_session_auth_hash(request, saved)
                    # Registra evento de segurança.
                    messages.success(request, _("Senha alterada com sucesso."))
            # Mensagem de sucesso genérica.
            messages.success(request, _("Alterações salvas com sucesso."))
        else:
            # Erros de validação são exibidos no formulário parcial.
            messages.error(request, _("Corrija os erros abaixo."))
        # Reconstrói contexto com o formulário (válido ou com erros).
        context: Dict[str, Any] = {
            f"{tab}_form": form,
            "tab": tab,
            "two_factor_enabled": self.get_two_factor_enabled(),
        }
        if tab == "preferencias" and form.is_valid():
            context["updated_preferences"] = True
        response = self.render_response(request, tab, context)
        # Atualiza cookies de tema e idioma após salvar preferências com sucesso.
        if tab == "preferencias" and form.is_valid():
            if hasattr(form, "instance"):
                tema = getattr(form.instance, "tema", None)
                idioma = getattr(form.instance, "idioma", None)
                if tema:
                    response.set_cookie(
                        "tema",
                        tema,
                        httponly=False,
                        secure=request.is_secure(),
                        samesite="Lax",
                    )
                if idioma:
                    response.set_cookie(
                        "django_language",
                        idioma,
                        httponly=False,
                        secure=request.is_secure(),
                        samesite="Lax",
                    )
        return response
