from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from accounts.models import UserType

from .forms import CategoriaDiscussaoForm, TopicoDiscussaoForm, RespostaDiscussaoForm
from .models import (
    CategoriaDiscussao,
    TopicoDiscussao,
    RespostaDiscussao,
    InteracaoDiscussao,
)


class CategoriaListView(LoginRequiredMixin, ListView):
    model = CategoriaDiscussao
    template_name = "discussao/categorias.html"
    context_object_name = "categorias"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("organizacao", "nucleo", "evento")
            .prefetch_related("topicos")
        )
        user = self.request.user
        if user.user_type != UserType.ROOT:
            qs = qs.filter(organizacao=user.organizacao)
        return qs


class TopicoListView(LoginRequiredMixin, ListView):
    model = TopicoDiscussao
    template_name = "discussao/topicos.html"
    context_object_name = "topicos"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            TopicoDiscussao.objects.filter(categoria=self.categoria)
            .select_related("categoria", "autor")
            .prefetch_related("respostas")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categoria"] = self.categoria
        return context


class TopicoDetailView(LoginRequiredMixin, DetailView):
    model = TopicoDiscussao
    template_name = "discussao/topico_detail.html"
    context_object_name = "topico"

    def get_object(self, queryset=None):
        categoria = get_object_or_404(CategoriaDiscussao, slug=self.kwargs["categoria_slug"])
        obj = get_object_or_404(
            TopicoDiscussao.objects.select_related("categoria", "autor")
            .prefetch_related("respostas__autor"),
            categoria=categoria,
            slug=self.kwargs["topico_slug"],
        )
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.incrementar_visualizacao()
        context = self.get_context_data(object=self.object)
        context["resposta_form"] = RespostaDiscussaoForm()
        return self.render_to_response(context)


class TopicoCreateView(LoginRequiredMixin, CreateView):
    model = TopicoDiscussao
    form_class = TopicoDiscussaoForm
    template_name = "discussao/topico_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR, UserType.ROOT}:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.categoria = self.categoria
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.object.slug])


class TopicoUpdateView(LoginRequiredMixin, UpdateView):
    model = TopicoDiscussao
    form_class = TopicoDiscussaoForm
    template_name = "discussao/topico_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        self.object = get_object_or_404(
            TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"]
        )
        if request.user != self.object.autor and request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.object.slug])


class TopicoDeleteView(LoginRequiredMixin, DeleteView):
    model = TopicoDiscussao
    template_name = "discussao/topico_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        self.object = get_object_or_404(
            TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"]
        )
        if request.user != self.object.autor and request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("discussao:topicos", args=[self.categoria.slug])


class RespostaCreateView(LoginRequiredMixin, CreateView):
    model = RespostaDiscussao
    form_class = RespostaDiscussaoForm
    template_name = "discussao/resposta_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        self.topico = get_object_or_404(
            TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"]
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.topico = self.topico
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.topico.slug])


class InteracaoView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id, tipo):
        content_type = get_object_or_404(ContentType, id=content_type_id)
        obj = get_object_or_404(content_type.model_class(), id=object_id)
        interacao, created = InteracaoDiscussao.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=object_id,
            defaults={"tipo": tipo},
        )
        if not created:
            if interacao.tipo == tipo:
                interacao.delete()
            else:
                interacao.tipo = tipo
                interacao.save()
        return HttpResponse(status=204)
