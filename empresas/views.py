from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
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

from .forms import ContatoEmpresaForm, EmpresaForm, TagForm, TagSearchForm
from .models import ContatoEmpresa, Empresa, EmpresaChangeLog, Tag
from .services import LOG_FIELDS, list_all_tags, registrar_alteracoes, search_empresas


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
        return search_empresas(self.request.user, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = list_all_tags()
        context["selected_tags"] = self.request.GET.getlist("tags")
        context["empresas"] = context.get("object_list")
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
        old_data = {campo: getattr(form.instance, campo) for campo in LOG_FIELDS}
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("cnpj", _("Empresa com este CNPJ já existe."))
            return self.form_invalid(form)
        registrar_alteracoes(self.request.user, self.object, old_data)
        messages.success(self.request, _("Empresa atualizada com sucesso."))
        return response


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
        empresa = self.get_empresa()
        user = self.request.user
        return user.is_superuser or user == empresa.usuario or user.user_type == UserType.ADMIN

    def get_empresa(self):
        if not hasattr(self, "_empresa"):
            self._empresa = get_object_or_404(Empresa, pk=self.kwargs["pk"])
        return self._empresa

    def get_queryset(self):
        return self.get_empresa().logs.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empresa"] = self.get_empresa()
        return context


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
    prod_tags = empresa.tags.filter(categoria=Tag.Categoria.PRODUTO)
    serv_tags = empresa.tags.filter(categoria=Tag.Categoria.SERVICO)
    context = {
        "empresa": empresa,
        "empresa_tags": empresa.tags.all(),
        "prod_tags": prod_tags,
        "serv_tags": serv_tags,
    }
    return render(request, "empresas/detail.htm", context)


# ------------------------------------------------------------------
# DELETAR
# ------------------------------------------------------------------
@login_required
@no_superadmin_required
def remover_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)

    if not pode_crud_empresa(request.user, empresa):
        return HttpResponseForbidden("Usuário não autorizado a remover esta empresa.")

    if request.method == "POST":
        empresa.soft_delete()
        if request.headers.get("HX-Request"):
            return JsonResponse({"message": "Empresa removida com sucesso."}, status=204)
        return redirect("empresas:lista")

    return render(request, "empresas/confirmar_remocao.html", {"empresa": empresa})


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
            form.save()
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
