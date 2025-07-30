from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Count, Max
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from accounts.models import UserType

from .forms import RespostaDiscussaoForm, TopicoDiscussaoForm
from .models import (
    CategoriaDiscussao,
    InteracaoDiscussao,
    RespostaDiscussao,
    TopicoDiscussao,
)


class CategoriaListView(LoginRequiredMixin, ListView):
    model = CategoriaDiscussao
    template_name = "discussao/categorias.html"
    context_object_name = "categorias"

    def get_queryset(self):
        qs = super().get_queryset().select_related("organizacao", "nucleo", "evento").prefetch_related("topicos")
        user = self.request.user
        if user.user_type != UserType.ROOT:
            qs = qs.filter(organizacao=user.organizacao)
        return qs


class TopicoListView(LoginRequiredMixin, ListView):
    model = TopicoDiscussao
    template_name = "discussao/topicos_list.html"
    context_object_name = "topicos"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        ordenacao = self.request.GET.get("ordenacao", "recentes")
        qs = (
            TopicoDiscussao.objects.filter(categoria=self.categoria)
            .select_related("categoria", "autor")
            .prefetch_related("respostas")
            .annotate(
                num_comentarios=Count("respostas"),
                last_activity=Max("respostas__created"),
            )
        )
        if ordenacao == "comentados":
            qs = qs.order_by("-num_comentarios")
        else:
            qs = qs.order_by("-created")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categoria"] = self.categoria
        context["ordenacao"] = self.request.GET.get("ordenacao", "recentes")
        return context


class TopicoDetailView(LoginRequiredMixin, DetailView):
    model = TopicoDiscussao
    template_name = "discussao/topico_detail.html"
    context_object_name = "topico"

    def get_object(self, queryset=None):
        categoria = get_object_or_404(CategoriaDiscussao, slug=self.kwargs["categoria_slug"])
        obj = get_object_or_404(
            TopicoDiscussao.objects.select_related("categoria", "autor").prefetch_related("respostas__autor"),
            categoria=categoria,
            slug=self.kwargs["topico_slug"],
        )
        return obj

    paginate_by = 10

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.incrementar_visualizacao()
        context = self.get_context_data(object=self.object)
        context["resposta_form"] = RespostaDiscussaoForm()
        if request.headers.get("Hx-Request"):
            return render(
                request,
                "discussao/topico_detail.html",
                {"comentarios": context["comentarios"], "partial": True, "user": request.user},
            )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comentarios_qs = self.object.respostas.select_related("autor")
        paginator = Paginator(comentarios_qs, self.paginate_by)
        page = self.request.GET.get("page")
        comentarios = paginator.get_page(page)
        context["comentarios"] = comentarios
        return context


class TopicoCreateView(LoginRequiredMixin, CreateView):
    model = TopicoDiscussao
    form_class = TopicoDiscussaoForm
    template_name = "discussao/topico_novo.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR, UserType.ROOT}:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.categoria = self.categoria
        response = super().form_valid(form)
        messages.success(self.request, gettext_lazy("T\u00f3pico criado com sucesso"))
        return response

    def get_success_url(self):
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.object.slug])


class TopicoUpdateView(LoginRequiredMixin, UpdateView):
    model = TopicoDiscussao
    form_class = TopicoDiscussaoForm
    template_name = "discussao/topico_novo.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        self.object = get_object_or_404(TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"])
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
        self.object = get_object_or_404(TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"])
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
        self.topico = get_object_or_404(TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.topico = self.topico
        response = super().form_valid(form)
        if self.request.headers.get("Hx-Request"):
            context = {"comentario": self.object, "user": self.request.user}
            return render(self.request, "discussao/comentario_item.html", context)
        messages.success(self.request, gettext_lazy("Coment\u00e1rio publicado"))
        return response

    def get_success_url(self):
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.topico.slug])


class RespostaDeleteView(LoginRequiredMixin, DeleteView):
    model = RespostaDiscussao

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(RespostaDiscussao, pk=kwargs["pk"])
        self.topico = self.object.topico
        if request.user != self.object.autor and request.user.get_tipo_usuario not in {
            UserType.ADMIN.value,
            UserType.COORDENADOR.value,
            UserType.ROOT.value,
        }:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        super().delete(request, *args, **kwargs)
        if request.headers.get("Hx-Request"):
            return HttpResponse("")
        messages.success(request, gettext_lazy("Coment\u00e1rio removido"))
        return redirect(
            "discussao:topico_detalhe",
            categoria_slug=self.topico.categoria.slug,
            topico_slug=self.topico.slug,
        )


class InteracaoView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id, tipo):
        content_type = get_object_or_404(ContentType, id=content_type_id)
        get_object_or_404(content_type.model_class(), id=object_id)
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
