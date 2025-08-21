from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from accounts.models import UserType
from core.permissions import (
    ClienteGerenteRequiredMixin,
    NoSuperadminMixin,
    no_superadmin_required,
    pode_crud_empresa,
)
from organizacoes.models import Organizacao

from .forms import AvaliacaoForm, ContatoEmpresaForm, EmpresaForm, TagForm, TagSearchForm
from .models import (
    AvaliacaoEmpresa,
    ContatoEmpresa,
    Empresa,
    EmpresaChangeLog,
    FavoritoEmpresa,
    Tag,
)
from .services import list_all_tags, search_empresas


@login_required
def buscar(request):
    empresas = search_empresas(request.user, request.GET)
    context = {"empresas": empresas, "q": request.GET.get("q", "")}
    if request.headers.get("HX-Request"):
        return render(request, "empresas/includes/empresas_table.html", context)
    return render(request, "empresas/busca.html", context)


class EmpresaListView(LoginRequiredMixin, ListView):
    model = Empresa
    template_name = "empresas/lista.html"
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if request.user.is_superuser or request.user.user_type in {
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.NUCLEADO,
        }:
            return super().dispatch(request, *args, **kwargs)
        return HttpResponseForbidden("Usuário não autorizado.")

    def get_queryset(self):
        params = self.request.GET.copy()
        if "organizacao" in params and "organizacao_id" not in params:
            params["organizacao_id"] = params.get("organizacao")

        qs = search_empresas(self.request.user, params)

        if not (
            self.request.GET.get("mostrar_excluidas") == "1"
            and self.request.user.user_type in {UserType.ADMIN, UserType.ROOT}
        ):
            qs = qs.filter(deleted=False)

        if self.request.user.is_authenticated:
            fav_exists = FavoritoEmpresa.objects.filter(
                usuario=self.request.user, empresa=OuterRef("pk"), deleted=False
            )
            qs = qs.annotate(favoritado=Exists(fav_exists))
        return qs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = list_all_tags()
        context["selected_tags"] = self.request.GET.getlist("tags")
        context["empresas"] = context.get("object_list")
        context["mostrar_excluidas"] = self.request.GET.get("mostrar_excluidas", "")
        if self.request.user.is_superuser or self.request.user.user_type == UserType.ADMIN:
            context["organizacoes"] = Organizacao.objects.all()
        else:
            org_id = getattr(self.request.user, "organizacao_id", None)
            context["organizacoes"] = (
                Organizacao.objects.filter(pk=org_id) if org_id else Organizacao.objects.none()
            )
        return context

    def get_template_names(self):  # type: ignore[override]
        if self.request.headers.get("HX-Request"):
            return ["empresas/includes/empresas_table.html"]
        return [self.template_name]


class EmpresaCreateView(LoginRequiredMixin, CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = "empresas/nova.html"
    success_url = reverse_lazy("empresas:lista")

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if not pode_crud_empresa(request.user):
            return HttpResponseForbidden("Usuário não autorizado a criar empresas.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.organizacao = self.request.user.organizacao
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("cnpj", _("Empresa com este CNPJ já existe."))
            return self.form_invalid(form)
        messages.success(self.request, _("Empresa criada com sucesso."))
        return response


class EmpresaUpdateView(LoginRequiredMixin, UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = "empresas/nova.html"
    success_url = reverse_lazy("empresas:lista")

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        self.empresa = self.get_object()
        if not pode_crud_empresa(request.user, self.empresa):
            return HttpResponseForbidden("Usuário não autorizado a editar esta empresa.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("cnpj", _("Empresa com este CNPJ já existe."))
            return self.form_invalid(form)
        messages.success(self.request, _("Empresa atualizada com sucesso."))
        return response


class EmpresaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Empresa
    template_name = "empresas/confirmar_remocao.html"
    success_url = reverse_lazy("empresas:lista")

    def test_func(self):
        return pode_crud_empresa(self.request.user, self.get_object())

    def delete(self, request, *args, **kwargs):  # type: ignore[override]
        empresa = self.get_object()
        empresa.soft_delete()
        EmpresaChangeLog.objects.create(
            empresa=empresa,
            usuario=request.user,
            campo_alterado="deleted",
            valor_antigo="False",
            valor_novo="True",
        )
        if request.headers.get("HX-Request"):
            return JsonResponse({"message": "Empresa removida com sucesso."}, status=HTTP_204_NO_CONTENT)
        messages.success(request, _("Empresa removida com sucesso."))
        return redirect(self.success_url)


class FavoritoListView(LoginRequiredMixin, ListView):
    model = Empresa
    template_name = "empresas/favoritos.html"
    context_object_name = "empresas"

    def get_queryset(self):
        return Empresa.objects.filter(favoritos__usuario=self.request.user, favoritos__deleted=False)


class TagListView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, ListView):
    model = Tag
    template_name = "empresas/tags_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        categoria = self.request.GET.get("categoria")
        if categoria in {Tag.Categoria.PRODUTO, Tag.Categoria.SERVICO}:
            qs = qs.filter(categoria=categoria)
        form = TagSearchForm(self.request.GET)
        if form.is_valid() and form.cleaned_data["tag"]:
            qs = qs.filter(pk=form.cleaned_data["tag"].pk)
        self.form = form
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = getattr(self, "form", TagSearchForm())
        return context


class TagCreateView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item criado com sucesso.")
        return super().form_valid(form)


class TagUpdateView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = "empresas/tag_form.html"
    success_url = reverse_lazy("empresas:tags_list")

    def form_valid(self, form):
        messages.success(self.request, "Item atualizado com sucesso.")
        return super().form_valid(form)


class TagDeleteView(NoSuperadminMixin, ClienteGerenteRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Tag
    template_name = "empresas/tag_confirm_delete.html"
    success_url = reverse_lazy("empresas:tags_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Item removido.")
        return super().delete(request, *args, **kwargs)


class EmpresaChangeLogListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = EmpresaChangeLog
    template_name = "empresas/historico.html"
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff

    def get_empresa(self):
        if not hasattr(self, "_empresa"):
            self._empresa = get_object_or_404(Empresa, pk=self.kwargs["pk"])
        return self._empresa

    def get_queryset(self):
        return self.get_empresa().logs.filter(deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empresa"] = self.get_empresa()
        return context


class AvaliacaoCreateView(LoginRequiredMixin, CreateView):
    model = AvaliacaoEmpresa
    form_class = AvaliacaoForm
    template_name = "empresas/avaliacao_form.html"

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        self.empresa = get_object_or_404(Empresa, pk=kwargs["empresa_id"])
        if AvaliacaoEmpresa.objects.filter(empresa=self.empresa, usuario=request.user, deleted=False).exists():
            return redirect("empresas:avaliacao_editar", empresa_id=self.empresa.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.empresa = self.empresa
        response = super().form_valid(form)
        messages.success(self.request, _("Avaliação registrada com sucesso."))
        if self.request.headers.get("HX-Request"):
            avaliacoes = self.empresa.avaliacoes.filter(deleted=False).select_related("usuario")
            context = {
                "empresa": self.empresa,
                "avaliacoes": avaliacoes,
                "media_avaliacoes": self.empresa.media_avaliacoes(),
                "avaliacao_usuario": avaliacoes.filter(usuario=self.request.user).first(),
            }
            return render(self.request, "empresas/includes/avaliacoes.html", context)
        return response

    def get_success_url(self):  # type: ignore[override]
        return reverse("empresas:detail", args=[self.empresa.pk])


class AvaliacaoUpdateView(LoginRequiredMixin, UpdateView):
    model = AvaliacaoEmpresa
    form_class = AvaliacaoForm
    template_name = "empresas/avaliacao_form.html"

    def get_object(self, queryset=None):  # type: ignore[override]
        self.empresa = get_object_or_404(Empresa, pk=self.kwargs["empresa_id"])
        avaliacao = AvaliacaoEmpresa.objects.filter(
            empresa=self.empresa, usuario=self.request.user, deleted=False
        ).first()
        if not avaliacao:
            messages.error(
                self.request, _("Você não possui nenhuma avaliação ativa para esta empresa.")
            )
            raise Http404
        return avaliacao

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Avaliação atualizada com sucesso."))
        if self.request.headers.get("HX-Request"):
            avaliacoes = self.empresa.avaliacoes.filter(deleted=False).select_related("usuario")
            context = {
                "empresa": self.empresa,
                "avaliacoes": avaliacoes,
                "media_avaliacoes": self.empresa.media_avaliacoes(),
                "avaliacao_usuario": avaliacoes.filter(usuario=self.request.user).first(),
            }
            return render(self.request, "empresas/includes/avaliacoes.html", context)
        return response

    def get_success_url(self):  # type: ignore[override]
        return reverse("empresas:detail", args=[self.empresa.pk])


# ------------------------------------------------------------------
# DETALHAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def detalhes_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if (
        not request.user.is_superuser
        and empresa.usuario.organizacao != request.user.organizacao  # Corrigido para usar 'organizacao'
    ):
        return HttpResponseForbidden()
    if request.user.is_authenticated:
        empresa.favoritado = FavoritoEmpresa.objects.filter(
            usuario=request.user, empresa=empresa, deleted=False
        ).exists()
    else:
        empresa.favoritado = False
    prod_tags = empresa.tags.filter(categoria=Tag.Categoria.PRODUTO)
    serv_tags = empresa.tags.filter(categoria=Tag.Categoria.SERVICO)
    avaliacoes = empresa.avaliacoes.filter(deleted=False).select_related("usuario")
    avaliacao_usuario = None
    if request.user.is_authenticated:
        avaliacao_usuario = avaliacoes.filter(usuario=request.user).first()
    pode_visualizar_contatos = pode_crud_empresa(request.user, empresa)
    contatos = []
    if pode_visualizar_contatos:
        contatos = list(empresa.contatos.filter(deleted=False))
    context = {
        "empresa": empresa,
        "empresa_tags": empresa.tags.all(),
        "prod_tags": prod_tags,
        "serv_tags": serv_tags,
        "avaliacoes": avaliacoes,
        "media_avaliacoes": empresa.media_avaliacoes(),
        "avaliacao_usuario": avaliacao_usuario,
        "contatos": contatos,
        "pode_visualizar_contatos": pode_visualizar_contatos,
    }
    return render(request, "empresas/detail.htm", context)


# ------------------------------------------------------------------
# DELETAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def adicionar_contato(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not pode_crud_empresa(request.user, empresa):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ContatoEmpresaForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.empresa = empresa
            contato.save()
            if request.headers.get("HX-Request"):
                context = {
                    "contato": contato,
                    "empresa": empresa,
                    "message": "Contato adicionado",
                }
                return render(request, "empresas/contato_form.html", context, status=HTTP_201_CREATED)
            return JsonResponse({"message": "Contato adicionado"}, status=HTTP_201_CREATED)
    else:
        form = ContatoEmpresaForm()
    return render(request, "empresas/contato_form.html", {"form": form, "empresa": empresa})


@login_required
@no_superadmin_required
def editar_contato(request, pk):
    contato = get_object_or_404(ContatoEmpresa, pk=pk)
    if not pode_crud_empresa(request.user, contato.empresa):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = ContatoEmpresaForm(request.POST, instance=contato)
        if form.is_valid():
            contato = form.save()
            if request.headers.get("HX-Request"):
                context = {
                    "contato": contato,
                    "empresa": contato.empresa,
                    "message": "Contato atualizado",
                }
                return render(request, "empresas/contato_form.html", context)
            return JsonResponse({"message": "Contato atualizado"}, status=200)
    else:
        form = ContatoEmpresaForm(instance=contato)
    return render(request, "empresas/contato_form.html", {"form": form, "empresa": contato.empresa})


@login_required
@no_superadmin_required
def remover_contato(request, pk):
    contato = get_object_or_404(ContatoEmpresa, pk=pk)
    if not pode_crud_empresa(request.user, contato.empresa):
        return HttpResponseForbidden()
    if request.method == "POST":
        contato.delete()
        return JsonResponse({}, status=HTTP_204_NO_CONTENT)
    return render(request, "empresas/contato_confirm_delete.html", {"contato": contato})
