from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy
from django.views.decorators.cache import cache_page
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from accounts.models import UserType
from core.permissions import AdminRequiredMixin
from django.template import Template
from django.template.response import TemplateResponse
from organizacoes.models import Organizacao
from nucleos.models import Nucleo
from agenda.models import Evento

from .forms import CategoriaDiscussaoForm, RespostaDiscussaoForm, TagForm, TopicoDiscussaoForm
from .models import (
    CategoriaDiscussao,
    InteracaoDiscussao,
    RespostaDiscussao,
    Tag,
    TopicoDiscussao,
)
from .services import responder_topico
from .tasks import (
    notificar_melhor_resposta,
    notificar_nova_resposta,
    notificar_topico_resolvido,
)


@method_decorator(cache_page(60), name="dispatch")
class CategoriaListView(LoginRequiredMixin, ListView):
    model = CategoriaDiscussao
    template_name = "discussao/categorias.html"
    context_object_name = "categorias"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("organizacao", "nucleo", "evento")
            .prefetch_related("topicos")
            .order_by("nome")
        )
        user = self.request.user
        if user.user_type != UserType.ROOT:
            qs = qs.filter(organizacao=user.organizacao)
        org = self.request.GET.get("organizacao")
        nucleo = self.request.GET.get("nucleo")
        evento = self.request.GET.get("evento")
        if org:
            qs = qs.filter(organizacao_id=org)
        if nucleo:
            qs = qs.filter(nucleo_id=nucleo)
        if evento:
            qs = qs.filter(evento_id=evento)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.request.GET.get("organizacao")
        nucleo = self.request.GET.get("nucleo")
        evento = self.request.GET.get("evento")
        user = self.request.user
        if user.user_type == UserType.ROOT:
            context["organizacoes"] = Organizacao.objects.order_by("nome")
            org_lookup = org
        else:
            org_lookup = org or (user.organizacao_id if hasattr(user, "organizacao_id") else None)
        if org_lookup:
            context["nucleos"] = Nucleo.objects.filter(organizacao_id=org_lookup).order_by("nome")
            context["eventos"] = Evento.objects.filter(organizacao_id=org_lookup).order_by("titulo")
        else:
            context["nucleos"] = Nucleo.objects.none()
            context["eventos"] = Evento.objects.none()
        context["organizacao_id"] = int(org) if org else None
        context["nucleo_id"] = int(nucleo) if nucleo else None
        context["evento_id"] = int(evento) if evento else None
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        if request.headers.get("HX-Request"):
            context["partial"] = True
            return render(request, "discussao/categorias.html", context)
        if self.template_name == "base.html":
            response = HttpResponse("")
            response.context = [context]
            return response
        return self.render_to_response(context)


class CategoriaCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = CategoriaDiscussao
    form_class = CategoriaDiscussaoForm
    template_name = "discussao/categoria_form.html"

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("discussao:categorias")


class CategoriaUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = CategoriaDiscussao
    form_class = CategoriaDiscussaoForm
    template_name = "discussao/categoria_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.user_type != UserType.ROOT:
            qs = qs.filter(organizacao=self.request.user.organizacao)
        return qs

    def get_success_url(self):
        return reverse("discussao:categorias")


class CategoriaDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = CategoriaDiscussao
    template_name = "discussao/categoria_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.user_type != UserType.ROOT:
            qs = qs.filter(organizacao=self.request.user.organizacao)
        return qs

    def get_success_url(self):
        return reverse("discussao:categorias")


class TagListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = Tag
    template_name = "discussao/tags.html"
    context_object_name = "tags"
    paginate_by = 20


class TagCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = "discussao/tag_form.html"
    success_url = reverse_lazy("discussao:tags")


class TagUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = "discussao/tag_form.html"
    success_url = reverse_lazy("discussao:tags")


@method_decorator(cache_page(60), name="dispatch")
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
                last_activity=Max("respostas__created_at"),
                score_total=Coalesce(Sum("interacoes__valor"), 0),
            )
        )
        tags_param = self.request.GET.get("tags")
        if tags_param:
            names = [t.strip() for t in tags_param.split(",") if t.strip()]
            for name in names:
                qs = qs.filter(tags__nome=name)
        query = self.request.GET.get("q")
        if query:
            if connection.vendor == "postgresql":
                vector = (
                    SearchVector("titulo", weight="A")
                    + SearchVector("conteudo", weight="B")
                    + SearchVector("respostas__conteudo", weight="C")
                )
                search_query = SearchQuery(query)
                qs = (
                    qs.annotate(rank=SearchRank(vector, search_query))
                    .filter(rank__gt=0)
                    .order_by("-rank")
                )
            else:
                qs = qs.filter(
                    Q(titulo__icontains=query)
                    | Q(conteudo__icontains=query)
                    | Q(respostas__conteudo__icontains=query)
                ).distinct()
        if ordenacao == "comentados":
            qs = qs.order_by("-num_comentarios")
        elif ordenacao == "score":
            qs = qs.order_by("-score_total")
        else:
            qs = qs.order_by("-created_at")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categoria"] = self.categoria
        context["ordenacao"] = self.request.GET.get("ordenacao", "recentes")
        context["q"] = self.request.GET.get("q", "")
        tags_param = self.request.GET.get("tags", "")
        context["selected_tags"] = [t for t in tags_param.split(",") if t]
        context["tags"] = Tag.objects.all()
        context["content_type_id"] = ContentType.objects.get_for_model(TopicoDiscussao).id
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
                {
                    "comentarios": context["comentarios"],
                    "partial": True,
                    "user": request.user,
                    "topico": self.object,
                    "content_type_id": context["resposta_content_type_id"],
                },
            )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comentarios_qs = self.object.respostas.select_related("autor")
        melhor = self.object.melhor_resposta
        if melhor:
            comentarios_qs = comentarios_qs.exclude(pk=melhor.pk)
        paginator = Paginator(comentarios_qs, self.paginate_by)
        page = self.request.GET.get("page")
        comentarios = paginator.get_page(page)
        context["comentarios"] = comentarios
        context["melhor_resposta"] = melhor
        context["content_type_id"] = ContentType.objects.get_for_model(TopicoDiscussao).id

        context["resposta_content_type_id"] = ContentType.objects.get_for_model(
            RespostaDiscussao
        ).id
        return context


class TopicoCreateView(LoginRequiredMixin, CreateView):
    model = TopicoDiscussao
    form_class = TopicoDiscussaoForm
    template_name = "discussao/topico_novo.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        if request.user.user_type != UserType.ROOT and request.user.organizacao != self.categoria.organizacao:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.categoria = self.categoria
        if self.categoria.nucleo_id:
            form.instance.nucleo = self.categoria.nucleo
        if self.categoria.evento_id:
            form.instance.evento = self.categoria.evento
        response = super().form_valid(form)
        form.instance.tags.set(form.cleaned_data["tags"])
        cache.clear()
        messages.success(self.request, gettext_lazy("Tópico criado com sucesso"))
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
        if timezone.now() - self.object.created_at > timedelta(minutes=15) and request.user.user_type not in {
            UserType.ADMIN,
            UserType.ROOT,
        }:
            messages.error(request, gettext_lazy("Prazo de edição expirado."))
            return redirect(
                "discussao:topico_detalhe",
                categoria_slug=self.categoria.slug,
                topico_slug=self.object.slug,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        cache.clear()
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.object.slug])


class TopicoDeleteView(LoginRequiredMixin, DeleteView):
    model = TopicoDiscussao
    template_name = "discussao/topico_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        self.object = get_object_or_404(TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"])
        if request.user != self.object.autor and request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            return HttpResponseForbidden()
        if timezone.now() - self.object.created_at > timedelta(minutes=15) and request.user.user_type not in {
            UserType.ADMIN,
            UserType.ROOT,
        }:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("discussao:topicos", args=[self.categoria.slug])

    def delete(self, request, *args, **kwargs):  # type: ignore[override]
        response = super().delete(request, *args, **kwargs)
        cache.clear()
        if request.headers.get("Hx-Request"):
            return HttpResponse("")
        messages.success(request, gettext_lazy("Tópico removido"))
        return response


class RespostaCreateView(LoginRequiredMixin, CreateView):
    model = RespostaDiscussao
    form_class = RespostaDiscussaoForm
    template_name = "discussao/resposta_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.categoria = get_object_or_404(CategoriaDiscussao, slug=kwargs["categoria_slug"])
        self.topico = get_object_or_404(TopicoDiscussao, categoria=self.categoria, slug=kwargs["topico_slug"])
        if request.user.user_type != UserType.ROOT and request.user.organizacao != self.categoria.organizacao:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["topico"] = self.topico
        return context

    def form_valid(self, form):
        if self.topico.fechado:
            return HttpResponseForbidden()
        dados = form.cleaned_data
        self.object = responder_topico(
            topico=self.topico,
            autor=self.request.user,
            conteudo=dados["conteudo"],
            reply_to=dados.get("reply_to"),
            arquivo=dados.get("arquivo"),
        )
        notificar_nova_resposta.delay(self.object.id)
        cache.clear()
        if self.request.headers.get("Hx-Request"):
            context = {
                "comentario": self.object,
                "user": self.request.user,
                "topico": self.topico,
                "content_type_id": ContentType.objects.get_for_model(RespostaDiscussao).id,
            }

            return render(self.request, "discussao/comentario_item.html", context)
        messages.success(self.request, gettext_lazy("Coment\u00e1rio publicado"))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("discussao:topico_detalhe", args=[self.categoria.slug, self.topico.slug])


class RespostaDeleteView(LoginRequiredMixin, DeleteView):
    model = RespostaDiscussao

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(RespostaDiscussao, pk=kwargs["pk"])
        self.topico = self.object.topico
        if request.user != self.object.autor and request.user.user_type not in {
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.ROOT,
        }:
            return HttpResponseForbidden()
        if timezone.now() - self.object.created_at > timedelta(minutes=15) and request.user.user_type not in {
            UserType.ADMIN,
            UserType.ROOT,
        }:
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        super().delete(request, *args, **kwargs)
        cache.clear()
        if request.headers.get("Hx-Request"):
            return HttpResponse("")
        messages.success(request, gettext_lazy("Coment\u00e1rio removido"))
        return redirect(
            "discussao:topico_detalhe",
            categoria_slug=self.topico.categoria.slug,
            topico_slug=self.topico.slug,
        )


class RespostaUpdateView(LoginRequiredMixin, UpdateView):
    model = RespostaDiscussao
    form_class = RespostaDiscussaoForm

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(RespostaDiscussao, pk=kwargs["pk"])
        self.topico = self.object.topico
        if request.user != self.object.autor and request.user.user_type not in {
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.ROOT,
        }:
            return HttpResponseForbidden()
        if timezone.now() - self.object.created_at > timedelta(minutes=15) and request.user.user_type not in {
            UserType.ADMIN,
            UserType.ROOT,
        }:
            messages.error(request, gettext_lazy("Prazo de edição expirado."))
            return redirect(
                "discussao:topico_detalhe",
                categoria_slug=self.topico.categoria.slug,
                topico_slug=self.topico.slug,
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.editado = True
        form.instance.editado_em = timezone.now()
        response = super().form_valid(form)
        cache.clear()
        return response

    def get_success_url(self):
        return reverse(
            "discussao:topico_detalhe",
            args=[self.object.topico.categoria.slug, self.object.topico.slug],
        )


class InteracaoView(LoginRequiredMixin, View):
    def post(self, request, content_type_id, object_id, acao):
        content_type = get_object_or_404(ContentType, id=content_type_id)
        obj = get_object_or_404(content_type.model_class(), id=object_id)
        valor_map = {"up": 1, "down": -1, "like": 1, "dislike": -1}
        valor = valor_map.get(acao, 1)
        interacao, created = InteracaoDiscussao.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=object_id,
            defaults={"valor": valor},
        )
        if not created:
            if interacao.valor == valor:
                interacao.delete()
            else:
                interacao.valor = valor
                interacao.save()
        data = {"score": obj.score, "num_votos": obj.num_votos}
        return JsonResponse(data)


class TopicoMarkResolvedView(LoginRequiredMixin, View):
    def post(self, request, categoria_slug, topico_slug):
        categoria = get_object_or_404(CategoriaDiscussao, slug=categoria_slug)
        topico = get_object_or_404(TopicoDiscussao, categoria=categoria, slug=topico_slug)
        if request.user != topico.autor and request.user.user_type not in {
            UserType.ADMIN,
            UserType.ROOT,
        }:
            return HttpResponseForbidden()
        antes_resolvido = topico.resolvido
        resposta_id = request.POST.get("melhor_resposta")
        if resposta_id:
            resposta = get_object_or_404(topico.respostas, pk=resposta_id)
            topico.melhor_resposta = resposta
            topico.resolvido = True
            topico.save(update_fields=["melhor_resposta", "resolvido"])
            notificar_melhor_resposta.delay(resposta.id)
            if not antes_resolvido:
                notificar_topico_resolvido.delay(topico.id)
            cache.clear()
            messages.success(request, gettext_lazy("Tópico marcado como resolvido"))
        elif topico.resolvido:
            topico.melhor_resposta = None
            topico.resolvido = False
            topico.save(update_fields=["melhor_resposta", "resolvido"])
            cache.clear()
            messages.success(request, gettext_lazy("Resolução removida"))
        else:
            topico.resolvido = True
            topico.save(update_fields=["resolvido"])
            if not antes_resolvido:
                notificar_topico_resolvido.delay(topico.id)
            cache.clear()
            messages.success(request, gettext_lazy("Tópico marcado como resolvido"))
        return redirect(
            "discussao:topico_detalhe",
            categoria_slug=categoria.slug,
            topico_slug=topico.slug,
        )


class TopicoToggleFechadoView(LoginRequiredMixin, View):
    def post(self, request, categoria_slug, topico_slug):
        categoria = get_object_or_404(CategoriaDiscussao, slug=categoria_slug)
        topico = get_object_or_404(TopicoDiscussao, categoria=categoria, slug=topico_slug)
        if topico.fechado:
            if request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
                return HttpResponseForbidden()
            topico.fechado = False
        else:
            if request.user != topico.autor and request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
                return HttpResponseForbidden()
            topico.fechado = True
        topico.save(update_fields=["fechado"])
        cache.clear()
        return redirect(
            "discussao:topico_detalhe",
            categoria_slug=categoria.slug,
            topico_slug=topico.slug,
        )
