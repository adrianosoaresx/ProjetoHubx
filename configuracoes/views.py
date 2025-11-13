from __future__ import annotations

from typing import Any, Dict

import json

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView, View

# Project‑specific imports.  These may vary depending on your actual project
# structure.  Adjust the module paths as necessary.
try:
    from configuracoes.forms import ConfiguracaoContaForm, OperadorCreateForm  # type: ignore
    from configuracoes.services import atualizar_preferencias_usuario, get_configuracao_conta  # type: ignore
    from accounts.models import AccountToken, UserType  # type: ignore
    from tokens.utils import get_client_ip  # type: ignore
except Exception:
    ConfiguracaoContaForm = None  # type: ignore
    OperadorCreateForm = None  # type: ignore
    def atualizar_preferencias_usuario(user, data):  # type: ignore
        return None
    def get_configuracao_conta(user):  # type: ignore
        return None
    class AccountToken:  # type: ignore
        class Tipo:
            PASSWORD_RESET = "password_reset"
        objects = None
    class UserType:  # type: ignore
        OPERADOR = "operador"
    def get_client_ip(request: HttpRequest) -> str:  # type: ignore
        return "0.0.0.0"

from core.permissions import AdminRequiredMixin


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

    # Mapeamento das seções para suas classes de formulário.
    form_classes: Dict[str, type[forms.Form]] = {
        "seguranca": PasswordChangeForm,
        "preferencias": ConfiguracaoContaForm,  # type: ignore
    }

    # Mapeamento das seções para seus templates de fragmento.
    partial_templates: Dict[str, str] = {
        "seguranca": "configuracoes/_partials/seguranca.html",
        "preferencias": "configuracoes/_partials/preferencias.html",
        "operadores": "configuracoes/_partials/operadores_panel.html",
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

    def get_form(self, section: str | None, data: Dict[str, Any] | None = None, files: Any | None = None) -> forms.Form | None:
        """
        Instancia o formulário correto para a aba atual.  Para a aba de segurança,
        o formulário recebe o usuário como primeiro parâmetro.  Para a aba de
        preferências, o formulário é construído a partir de uma instância de
        configuração da conta.
        """
        section = section or "seguranca"
        if section not in self.form_classes:
            return None  # type: ignore[return-value]
        form_class = self.form_classes[section]
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

    def resolve_section(self, request: HttpRequest) -> str:
        """
        Resolve o valor da aba a partir dos parâmetros GET ou POST.  Valores
        inválidos são normalizados para ``seguranca``.
        """
        # Prioriza a seção vinda da rota (kwargs) e, em seguida, POST; ignora query string
        section = self.kwargs.get("section") or request.POST.get("section") or "seguranca"
        # Redireciona seções externas para seus respectivos módulos.
        if section in {"informacoes", "redes"}:
            return section
        if section not in {"seguranca", "preferencias", "operadores"}:
            raise Http404
        return section

    def get_panel_target_ids(self) -> Dict[str, str]:
        """Retorna os IDs utilizados como destino dos fragmentos HTMX."""

        return {
            "seguranca": "seguranca-panel-content",
            "preferencias": "preferencias-panel-content",
            "operadores": "operadores-panel-content",
        }

    def _augment_panel_context(self, context: Dict[str, Any], section: str) -> None:
        """Adiciona ao contexto os IDs de destino para cada painel do acordeão."""

        panel_ids = self.get_panel_target_ids()
        context.setdefault("seguranca_panel_target_id", panel_ids["seguranca"])
        context.setdefault("preferencias_panel_target_id", panel_ids["preferencias"])
        context.setdefault("operadores_panel_target_id", panel_ids["operadores"])
        context["hx_target_id"] = panel_ids.get(section, "settings-content")

    def _ensure_full_page_forms(self, context: Dict[str, Any]) -> None:
        """Garante que todos os formulários estejam disponíveis para o template completo."""

        for section, form_class in self.form_classes.items():
            if form_class is None:
                continue
            context.setdefault(f"{section}_form", self.get_form(section))

    def can_manage_operadores(self) -> bool:
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return True
        user_type = getattr(user, "user_type", None)
        user_type_value = getattr(user_type, "value", user_type)
        allowed_types = {
            getattr(getattr(UserType, "ROOT", "root"), "value", getattr(UserType, "ROOT", "root")),
            getattr(getattr(UserType, "ADMIN", "admin"), "value", getattr(UserType, "ADMIN", "admin")),
        }
        return user_type_value in allowed_types

    def get_operadores_queryset(self):
        User = get_user_model()
        operador_value = getattr(UserType.OPERADOR, "value", UserType.OPERADOR)  # type: ignore[attr-defined]
        qs = User.objects.filter(user_type=operador_value)
        user_org_id = getattr(self.request.user, "organizacao_id", None)
        user_type_value = getattr(getattr(self.request.user, "user_type", None), "value", getattr(self.request.user, "user_type", None))
        if user_org_id and user_type_value != getattr(getattr(UserType, "ROOT", "root"), "value", getattr(UserType, "ROOT", "root")):
            qs = qs.filter(organizacao_id=user_org_id)
        return qs.select_related("organizacao").order_by("contato", "username")

    def get_operadores_context(self) -> Dict[str, Any]:
        if not self.can_manage_operadores():
            return {
                "operadores": [],
                "can_manage_operadores": False,
            }
        return {
            "operadores": self.get_operadores_queryset(),
            "can_manage_operadores": True,
        }

    def render_response(self, request: HttpRequest, section: str, context: Dict[str, Any]) -> HttpResponse:
        """
        Renderiza a resposta apropriada para a aba, retornando um fragmento HTMX
        quando a requisição for feita via HTMX.  Adiciona o cabeçalho Vary para
        distinguir a cache entre HTMX e requests normais.
        """
        # Identifica requisição HTMX de forma robusta.
        is_htmx = _is_htmx(request)
        template = (
            self.partial_templates.get(section, self.partial_templates["seguranca"])
            if is_htmx
            else "configuracoes/configuracao.html"
        )
        if not is_htmx:
            self._ensure_full_page_forms(context)
        if section == "operadores" or not is_htmx:
            operadores_context = self.get_operadores_context()
            context.setdefault("operadores", operadores_context.get("operadores", []))
            context.setdefault("can_manage_operadores", operadores_context.get("can_manage_operadores", False))
        self._augment_panel_context(context, section)
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

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Manipula requisições GET.  Para abas externas, redireciona de imediato.
        Em seguida, prepara o contexto necessário (formulário correto, aba ativa,
        status do 2FA) e delega a renderização a ``render_response``.
        """
        section = self.resolve_section(request)
        # Redireciona seções que pertencem a outros apps.
        if section in {"informacoes", "redes"}:
            return redirect("accounts:perfil_sections_info")
        form = self.get_form(section)
        hero_titles = {
            "seguranca": _("Segurança"),
            "preferencias": _("Preferências"),
            "operadores": _("Operadores"),
        }
        hero_subtitles = {
            "seguranca": _("Personalize segurança, preferências e operadores da sua conta."),
            "preferencias": _("Personalize segurança, preferências e operadores da sua conta."),
            "operadores": _("Gerencie os operadores da sua organização."),
        }
        hero_title = hero_titles.get(section, _("Configurações"))
        context: Dict[str, Any] = {
            "tab": section,  # manter compat com templates existentes
            "two_factor_enabled": self.get_two_factor_enabled(),
            "hero_title": hero_title,
            "hero_subtitle": hero_subtitles.get(section, _("Personalize segurança, preferências e operadores da sua conta.")),
            "hero_active_tab": section,
        }
        if form is not None:
            context[f"{section}_form"] = form
        if section == "operadores":
            context.update(self.get_operadores_context())
        return self.render_response(request, section, context)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Manipula requisições POST.  Valida o formulário correspondente e
        persiste alterações quando possível.  Retorna sempre o fragmento HTMX em
        requisições HTMX, permitindo atualização assíncrona do conteúdo.
        """
        section = self.resolve_section(request)
        if section in {"informacoes", "redes"}:
            return redirect("accounts:perfil_sections_info")
        if section == "operadores":
            return self.get(request, *args, **kwargs)
        # Instancia o formulário apropriado com os dados recebidos.
        form = self.get_form(section, request.POST, request.FILES)
        if form.is_valid():
            # Persistir alterações conforme o tipo de formulário.
            if section == "preferencias" and atualizar_preferencias_usuario is not None:
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
        hero_titles = {
            "seguranca": _("Segurança"),
            "preferencias": _("Preferências"),
        }
        hero_subtitles = {
            "seguranca": _("Personalize segurança, preferências e operadores da sua conta."),
            "preferencias": _("Personalize segurança, preferências e operadores da sua conta."),
        }
        hero_title = hero_titles.get(section, _("Configurações"))
        context: Dict[str, Any] = {
            "tab": section,  # manter compat com templates existentes
            "two_factor_enabled": self.get_two_factor_enabled(),
            "hero_title": hero_title,
            "hero_subtitle": hero_subtitles.get(section, _("Personalize segurança, preferências e operadores da sua conta.")),
            "hero_active_tab": section,
        }
        if form is not None:
            context[f"{section}_form"] = form
        if section == "preferencias" and form.is_valid():
            context["updated_preferences"] = True
        response = self.render_response(request, section, context)
        # Atualiza cookies de tema e idioma após salvar preferências com sucesso.
        if section == "preferencias" and form.is_valid():
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


class OperadorListView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Retorna o fragmento da lista de operadores para o painel de configurações."""

    template_name = "configuracoes/_partials/operadores_lista.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if UserType is None:  # type: ignore
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not _is_htmx(request):
            return redirect(reverse("configuracoes:configuracoes_operadores"))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        operador_value = getattr(UserType.OPERADOR, "value", UserType.OPERADOR)  # type: ignore[attr-defined]
        qs = User.objects.filter(user_type=operador_value)
        user_org_id = getattr(self.request.user, "organizacao_id", None)
        user_type_value = getattr(getattr(self.request.user, "user_type", None), "value", getattr(self.request.user, "user_type", None))
        if user_org_id and user_type_value != getattr(UserType.ROOT, "value", UserType.ROOT):  # type: ignore[attr-defined]
            qs = qs.filter(organizacao_id=user_org_id)
        operadores = qs.select_related("organizacao").order_by("contato", "username")
        context.update(
            {
                "operadores": operadores,
                "can_manage_operadores": True,
            }
        )
        return context


class OperadorCreateView(LoginRequiredMixin, AdminRequiredMixin, FormView):
    """Formulário para criação de usuários operadores."""

    template_name = "configuracoes/_partials/operador_form.html"
    form_class = OperadorCreateForm  # type: ignore[assignment]
    success_url = reverse_lazy("configuracoes:configuracoes_operadores")

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if OperadorCreateForm is None:  # type: ignore
            raise Http404("Formulário de operador não disponível.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not _is_htmx(request):
            return redirect(reverse("configuracoes:configuracoes_operadores"))
        return super().get(request, *args, **kwargs)

    def get_form_class(self):  # type: ignore[override]
        if OperadorCreateForm is None:  # type: ignore
            raise Http404("Formulário de operador não disponível.")
        return OperadorCreateForm

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": _("Adicionar operador"),
                "form_description": _("Informe os dados básicos para criar um novo usuário operador."),
                "form_action": self.request.get_full_path(),
            }
        )
        return context

    def form_valid(self, form: OperadorCreateForm) -> HttpResponse:  # type: ignore[override]
        organizacao = getattr(self.request.user, "organizacao", None)
        saved_user = form.save(organizacao=organizacao)  # type: ignore[attr-defined]
        messages.success(
            self.request,
            _("Operador %(username)s criado com sucesso.")
            % {"username": getattr(saved_user, "username", "")},
        )
        self.object = saved_user  # type: ignore[assignment]
        if _is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps({"operadores:refresh": True, "modal:close": True})
            return response
        return super().form_valid(form)
