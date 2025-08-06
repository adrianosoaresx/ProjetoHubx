from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView

from accounts.models import UserType
from nucleos.models import Nucleo

from .forms import CommentForm, LikeForm, PostForm
from .models import Like, ModeracaoPost, Post
from .services import upload_media


@login_required
def meu_mural(request):
    """Exibe o mural pessoal do usuário com seus posts e posts globais."""

    posts = (
        Post.objects.select_related("autor", "organizacao", "nucleo", "evento", "moderacao")
        .prefetch_related("likes", "comments")
        .filter(deleted=False)
        .exclude(moderacao__status="rejeitado")
        .filter(
            Q(autor=request.user)
            | Q(
                tipo_feed="global",
                organizacao=request.user.organizacao,
                moderacao__status="aprovado",
            )
        )
        .order_by("-created_at")
        .distinct()
    )

    context = {
        "posts": posts,
        "nucleos_do_usuario": Nucleo.objects.filter(participacoes__user=request.user),
    }
    return render(request, "feed/mural.html", context)


class FeedListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "feed/feed.html"
    context_object_name = "posts"
    paginate_by = 15

    cache_timeout = 60

    def _cache_key(self, request) -> str:
        params = request.GET
        keys = [
            str(request.user.pk),
            *(params.get(k, "") for k in [
                "tipo_feed",
                "organizacao",
                "nucleo",
                "evento",
                "tags",
                "page",
                "q",
            ]),
        ]
        return "feed:list:" + ":".join(keys)

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        key = self._cache_key(request)
        cached = cache.get(key)
        if cached:
            return cached
        response = super().dispatch(request, *args, **kwargs)
        cache.set(key, response, self.cache_timeout)
        return response

    def get_queryset(self):
        tipo_feed = self.request.GET.get("tipo_feed", "global")
        q = self.request.GET.get("q", "").strip()
        user = self.request.user

        qs = Post.objects.select_related("autor", "organizacao", "nucleo", "evento", "moderacao").prefetch_related(
            "likes", "comments", "tags"
        )
        qs = qs.filter(deleted=False).exclude(moderacao__status="rejeitado")
        if not user.is_staff:
            qs = qs.filter(Q(moderacao__status="aprovado") | Q(autor=user))
        qs = qs.distinct()

        if tipo_feed == "usuario":
            qs = qs.filter(Q(autor=user) | Q(tipo_feed="global", organizacao=user.organizacao))
        elif tipo_feed == "nucleo":
            nucleo_id = self.request.GET.get("nucleo")
            qs = qs.filter(tipo_feed="nucleo", nucleo_id=nucleo_id)
            from nucleos.models import Nucleo

            if not Nucleo.objects.filter(id=nucleo_id, participacoes__user=user).exists():
                qs = qs.none()
        elif tipo_feed == "evento":
            evento_id = self.request.GET.get("evento")
            qs = qs.filter(tipo_feed="evento", evento_id=evento_id)
        else:  # global
            qs = qs.filter(tipo_feed="global")
            if user.user_type != UserType.ROOT:
                qs = qs.filter(organizacao=user.organizacao)

        if q:
            or_terms = [t.strip() for t in q.split("|") if t.strip()]
            if connection.vendor == "postgresql":
                query_parts = [" & ".join(term.split()) for term in or_terms]
                query = SearchQuery(" | ".join(query_parts), config="portuguese")
                vector = (
                    SearchVector("conteudo", config="portuguese")
                    + SearchVector("tags__nome", config="portuguese")
                )
                qs = (
                    qs.annotate(search=vector, rank=SearchRank(vector, query))
                    .filter(search=query)
                    .order_by("-rank")
                )
            else:  # fallback para sqlite
                or_query = Q()
                for term in or_terms:
                    sub = Q()
                    for part in term.split():
                        sub &= Q(conteudo__icontains=part) | Q(tags__nome__icontains=part)
                    or_query |= sub
                qs = qs.filter(or_query)
        tags_param = self.request.GET.get("tags")
        if tags_param:
            tag_names = [t.strip() for t in tags_param.split(",") if t.strip()]
            qs = qs.filter(tags__nome__in=tag_names).distinct()

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nucleos_do_usuario"] = Nucleo.objects.filter(participacoes__user=self.request.user)
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            return render(self.request, "feed/_grid.html", context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)


class NovaPostagemView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "feed/nova_postagem.html"
    success_url = reverse_lazy("feed:meu_mural")

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type == UserType.ROOT:
            return HttpResponseForbidden("Usuário root não pode publicar no feed.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        file = self.request.FILES.get("arquivo")
        if file:
            files = self.request.FILES.copy()
            if file.content_type == "application/pdf" or file.name.lower().endswith(".pdf"):
                files["pdf"] = file
            elif file.content_type.startswith("video/"):
                files["video"] = file
            else:
                files["image"] = file
            kwargs["files"] = files
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nucleos_do_usuario"] = Nucleo.objects.filter(participacoes__user=self.request.user)
        return context

    def form_valid(self, form):
        for field in ["image", "pdf", "video"]:
            file = form.cleaned_data.get(field)
            if file:
                setattr(form.instance, field, upload_media(file))
        form.instance.autor = self.request.user
        form.instance.organizacao = self.request.user.organizacao
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Redirect": self.get_success_url()})
        return response


class PostDetailView(LoginRequiredMixin, DetailView):
    template_name = "feed/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        qs = Post.objects.select_related("autor", "organizacao", "nucleo", "evento", "moderacao").prefetch_related(
            "tags"
        )
        qs = qs.filter(deleted=False).exclude(moderacao__status="rejeitado")
        if not self.request.user.is_staff:
            qs = qs.filter(Q(moderacao__status="aprovado") | Q(autor=self.request.user))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CommentForm()
        context["like_form"] = LikeForm()
        return context


@login_required
def create_comment(request, pk):
    post = get_object_or_404(Post.objects.filter(deleted=False), id=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.post = post
        comment.save()
        if request.headers.get("HX-Request"):
            html = render_to_string("feed/_comment.html", {"comment": comment}, request=request)
            return HttpResponse(html)
        return redirect("feed:post_detail", pk=post.id)
    if request.headers.get("HX-Request"):
        html = render_to_string(
            "feed/post_detail.html",
            {"post": post, "comment_form": form},
            request=request,
        )
        return HttpResponse(html, status=400)
    return render(request, "feed/post_detail.html", {"post": post, "comment_form": form})


@login_required
def toggle_like(request, pk):
    post = get_object_or_404(Post.objects.filter(deleted=False), id=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    if request.headers.get("HX-Request"):
        html = render_to_string("feed/_like_button.html", {"post": post, "user": request.user}, request=request)
        return HttpResponse(html)
    return redirect("feed:post_detail", pk=post.id)


@login_required
def post_update(request, pk):
    post = get_object_or_404(Post.objects.filter(deleted=False), pk=pk)
    if request.user != post.autor and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        if request.headers.get("HX-Request"):
            return HttpResponseForbidden()
        messages.error(request, "Você não tem permissão para editar esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        files = request.FILES
        file = request.FILES.get("arquivo")
        if file:
            files = request.FILES.copy()
            if file.content_type == "application/pdf" or file.name.lower().endswith(".pdf"):
                files["pdf"] = file
            elif file.content_type.startswith("video/"):
                files["video"] = file
            else:
                files["image"] = file
        form = PostForm(request.POST, files, instance=post, user=request.user)
        if form.is_valid():
            for field in ["image", "pdf", "video"]:
                file = form.cleaned_data.get(field)
                if file:
                    setattr(form.instance, field, upload_media(file))
            form.instance.organizacao = request.user.organizacao
            form.save()
            if request.headers.get("HX-Request"):
                return HttpResponse(status=204, headers={"HX-Redirect": reverse("feed:post_detail", args=[post.pk])})
            messages.success(request, "Postagem atualizada com sucesso.")
            return redirect("feed:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post, user=request.user)

    return render(request, "feed/post_update.html", {"form": form, "post": post})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post.objects.filter(deleted=False), pk=pk)
    if request.user != post.autor and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        if request.headers.get("HX-Request"):
            return HttpResponseForbidden()
        messages.error(request, "Você não tem permissão para remover esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        post.soft_delete()
        if request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Redirect": reverse("feed:listar")})
        messages.success(request, "Postagem removida.")
        return redirect("feed:listar")

    return render(request, "feed/post_delete.html", {"post": post})


@login_required
@permission_required("feed.change_post", raise_exception=True)
def moderar_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    mod, _ = ModeracaoPost.objects.get_or_create(post=post)
    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "aprovar":
            mod.status = "aprovado"
            mod.avaliado_por = request.user
            mod.avaliado_em = timezone.now()
            mod.save(update_fields=["status", "avaliado_por", "avaliado_em", "updated_at"])
        elif acao == "rejeitar":
            mod.status = "rejeitado"
            mod.motivo = request.POST.get("motivo", "")
            mod.avaliado_por = request.user
            mod.avaliado_em = timezone.now()
            mod.save(update_fields=["status", "motivo", "avaliado_por", "avaliado_em", "updated_at"])
    return redirect("feed:post_detail", pk=pk)
