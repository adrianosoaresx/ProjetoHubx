from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView
from django_ratelimit.core import is_ratelimited

from accounts.models import UserType
from agenda.models import Evento
from core.cache import get_cache_version
from core.permissions import NoSuperadminMixin, no_superadmin_required
# Moderação desativada: não é necessário notificar moderação
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .api import _post_rate, _read_rate
from .forms import CommentForm, PostForm
from .models import Bookmark, Flag, Post, Reacao, Tag


@login_required
@no_superadmin_required
def meu_mural(request):
    """Exibe o mural pessoal do usuário com seus posts e posts globais."""

    posts = (
        Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
        .prefetch_related("reacoes", "comments")
        .filter(deleted=False)
        .annotate(
            like_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="like", reacoes__deleted=False),
                distinct=True,
            ),
            share_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="share", reacoes__deleted=False),
                distinct=True,
            ),
            is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)),
            is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)),
            is_liked=Exists(Reacao.objects.filter(post=OuterRef("pk"), user=request.user, vote="like", deleted=False)),
            is_shared=Exists(
                Reacao.objects.filter(post=OuterRef("pk"), user=request.user, vote="share", deleted=False)
            ),
        )
        .filter(
            Q(autor=request.user)
            | Q(
                tipo_feed="global",
                organizacao=request.user.organizacao,
                mod_status="aprovado",
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


@login_required
@no_superadmin_required
def bookmark_list(request):
    posts = (
        Post.objects.filter(bookmarks__user=request.user, bookmarks__deleted=False, deleted=False)
        .select_related("autor", "organizacao", "nucleo", "evento")
        .prefetch_related("comments", "bookmarks", "flags", "reacoes")
        .annotate(
            like_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="like", reacoes__deleted=False),
                distinct=True,
            ),
            share_count=Count(
                "reacoes",
                filter=Q(reacoes__vote="share", reacoes__deleted=False),
                distinct=True,
            ),
            is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)),
            is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)),
            is_liked=Exists(Reacao.objects.filter(post=OuterRef("pk"), user=request.user, vote="like", deleted=False)),
            is_shared=Exists(
                Reacao.objects.filter(post=OuterRef("pk"), user=request.user, vote="share", deleted=False)
            ),
        )
        .order_by("-bookmarks__created_at")
        .distinct()
    )
    return render(request, "feed/bookmarks.html", {"posts": posts})


class FeedListView(LoginRequiredMixin, NoSuperadminMixin, ListView):
    model = Post
    template_name = "feed/feed.html"
    context_object_name = "posts"
    paginate_by = 15

    cache_timeout = 60

    def _cache_key(self, request) -> str:
        params = request.GET
        version = get_cache_version("feed_list")
        keys = [
            str(request.user.pk),
            *(
                params.get(k, "")
                for k in [
                    "tipo_feed",
                    "organizacao",
                    "nucleo",
                    "evento",
                    "tags",
                    "date_from",
                    "date_to",
                    "page",
                    "q",
                ]
            ),
        ]
        return f"feed:list:v{version}:" + ":".join(keys)

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if is_ratelimited(
            request,
            group="feed_posts_list",
            key="user",
            rate=_read_rate(None, request),
            method="GET",
            increment=True,
        ):
            return HttpResponse(_("Limite de requisições excedido."), status=429)
        key = self._cache_key(request)
        cached = cache.get(key)
        if cached:
            return cached
        response = super().dispatch(request, *args, **kwargs)
        response.render()
        cache.set(key, response, self.cache_timeout)
        return response

    def get_queryset(self):
        tipo_feed = self.request.GET.get("tipo_feed", "global")
        q = self.request.GET.get("q", "").strip()
        user = self.request.user
        organizacao_id = self.request.GET.get("organizacao")

        qs = Post.objects.select_related("autor", "organizacao", "nucleo", "evento").prefetch_related(
            "reacoes",
            "comments",
            "tags",
            "bookmarks",
            "flags",
        )
        qs = (
            qs.filter(deleted=False)
            .annotate(
                like_count=Count(
                    "reacoes",
                    filter=Q(reacoes__vote="like", reacoes__deleted=False),
                    distinct=True,
                ),
                share_count=Count(
                    "reacoes",
                    filter=Q(reacoes__vote="share", reacoes__deleted=False),
                    distinct=True,
                ),
                is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=user, deleted=False)),
                is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=user, deleted=False)),
                is_liked=Exists(Reacao.objects.filter(post=OuterRef("pk"), user=user, vote="like", deleted=False)),
                is_shared=Exists(Reacao.objects.filter(post=OuterRef("pk"), user=user, vote="share", deleted=False)),
            )
        )
        # Moderação desativada: usuários veem seus posts e o feed global da organização
        if not user.is_staff:
            qs = qs.filter(Q(autor=user) | Q(tipo_feed="global"))
        qs = qs.distinct()

        if organizacao_id:
            qs = qs.filter(organizacao_id=organizacao_id)

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
            if not organizacao_id and user.user_type != UserType.ROOT:
                qs = qs.filter(organizacao=user.organizacao)

        if q:
            or_terms = [t.strip() for t in q.split("|") if t.strip()]
            if connection.vendor == "postgresql":
                query_parts = [" & ".join(term.split()) for term in or_terms]
                query = SearchQuery(" | ".join(query_parts), config="portuguese")
                vector = SearchVector("conteudo", config="portuguese") + SearchVector("tags__nome", config="portuguese")
                qs = (
                    qs.annotate(search=vector, rank=SearchRank(vector, query))
                    .filter(search=query)
                    .filter(Q(tags__deleted=False) | Q(tags__isnull=True))
                    .order_by("-rank")
                )
            else:  # fallback para sqlite
                or_query = Q()
                for term in or_terms:
                    sub = Q()
                    for part in term.split():
                        sub &= Q(conteudo__icontains=part) | Q(tags__nome__icontains=part, tags__deleted=False)
                    or_query |= sub
                qs = qs.filter(or_query)
        tags_param = self.request.GET.get("tags")
        if tags_param:
            tag_names = [t.strip() for t in tags_param.split(",") if t.strip()]
            qs = qs.filter(tags__nome__in=tag_names, tags__deleted=False).distinct()

        date_from = self.request.GET.get("date_from")
        if date_from:
            try:
                df = datetime.fromisoformat(date_from).date()
                qs = qs.filter(created_at__date__gte=df)
            except ValueError:
                pass

        date_to = self.request.GET.get("date_to")
        if date_to:
            try:
                dt = datetime.fromisoformat(date_to).date()
                qs = qs.filter(created_at__date__lte=dt)
            except ValueError:
                pass

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        context["nucleos_do_usuario"] = Nucleo.objects.filter(participacoes__user=user)
        context["tags_disponiveis"] = Tag.objects.all()
        if hasattr(user, "eventos"):
            context["eventos_do_usuario"] = user.eventos.all()
        else:
            context["eventos_do_usuario"] = Evento.objects.none()
        if user.user_type in {UserType.ROOT, UserType.ADMIN}:
            context["organizacoes_do_usuario"] = Organizacao.objects.all()
        else:
            org = getattr(user, "organizacao", None)
            context["organizacoes_do_usuario"] = (
                Organizacao.objects.filter(pk=org.pk) if org else Organizacao.objects.none()
            )

        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            return render(self.request, "feed/_grid.html", context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)


class NovaPostagemView(LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "feed/nova_postagem.html"
    success_url = reverse_lazy("feed:meu_mural")

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST" and is_ratelimited(
            request,
            group="feed_posts_create",
            key="user",
            rate=_post_rate(None, request),
            method="POST",
            increment=True,
        ):
            messages.error(request, _("Limite de postagens excedido."))
            return HttpResponse(_("Limite de requisições excedido."), status=429)
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
            value = form.cleaned_data.get(field)
            if value:
                setattr(form.instance, field, value)
        if getattr(form, "_video_preview_key", None):
            form.instance.video_preview = form._video_preview_key
        form.instance.autor = self.request.user
        form.instance.organizacao = form.cleaned_data.get("organizacao") or self.request.user.organizacao
        response = super().form_valid(form)

        # Processa tags digitadas no campo de texto (separadas por vírgula)
        tags_text = (self.request.POST.get("tags_text", "") or "").strip()
        if tags_text:
            tag_names = [t.strip() for t in tags_text.split(",") if t.strip()]
            if tag_names:
                tags_qs = Tag.objects.filter(nome__in=tag_names, deleted=False)
                # Associa apenas tags existentes nesta versão
                self.object.tags.set(list(tags_qs))
        from feed.tasks import POSTS_CREATED, notify_new_post

        POSTS_CREATED.inc()
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notify_new_post(str(self.object.id))
        else:
            notify_new_post.delay(str(self.object.id))
        # Se for uma requisição via HTMX, retornar instrução de redirecionamento
        if self.request.headers.get("HX-Request"):
            return HttpResponse(status=204, headers={"HX-Redirect": self.get_success_url()})
        return response

    def form_invalid(self, form):  # type: ignore[override]
        """Em requisições HTMX, devolve apenas o formulário com status 422.

        Isso evita que a página inteira seja aninhada dentro do formulário
        e permite que o hx-select/hx-target faça o swap corretamente.
        """
        if self.request.headers.get("HX-Request"):
            html = render(self.request, self.template_name, self.get_context_data(form=form)).content
            return HttpResponse(html, status=422)
        return super().form_invalid(form)


class PostDetailView(LoginRequiredMixin, NoSuperadminMixin, DetailView):
    template_name = "feed/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        qs = Post.objects.select_related("autor", "organizacao", "nucleo", "evento").prefetch_related("tags")
        qs = (
            qs.filter(deleted=False)
            .annotate(
                like_count=Count(
                    "reacoes",
                    filter=Q(reacoes__vote="like", reacoes__deleted=False),
                    distinct=True,
                ),
                share_count=Count(
                    "reacoes",
                    filter=Q(reacoes__vote="share", reacoes__deleted=False),
                    distinct=True,
                ),
                is_bookmarked=Exists(
                    Bookmark.objects.filter(post=OuterRef("pk"), user=self.request.user, deleted=False)
                ),
                is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=self.request.user, deleted=False)),
                is_liked=Exists(
                    Reacao.objects.filter(post=OuterRef("pk"), user=self.request.user, vote="like", deleted=False)
                ),
                is_shared=Exists(
                    Reacao.objects.filter(post=OuterRef("pk"), user=self.request.user, vote="share", deleted=False)
                ),
            )
        )
        if not self.request.user.is_staff:
            qs = qs.filter(Q(autor=self.request.user) | Q(tipo_feed="global"))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CommentForm(initial={"post": self.object.id})
        return context


@login_required
@no_superadmin_required
def toggle_like(request, pk):
    if is_ratelimited(
        request,
        group="feed_misc_actions",
        key="user",
        rate=_read_rate(None, request),
        method="POST",
        increment=True,
    ):
        return HttpResponse(status=429)
    post = get_object_or_404(Post.objects.filter(deleted=False), id=pk)
    reacao = Reacao.all_objects.filter(post=post, user=request.user, vote="like").first()
    if reacao and not reacao.deleted:
        reacao.deleted = True
        reacao.save(update_fields=["deleted"])
    elif reacao:
        reacao.deleted = False
        reacao.save(update_fields=["deleted"])
    else:
        Reacao.objects.create(post=post, user=request.user, vote="like")
    if request.headers.get("HX-Request"):
        html = render_to_string("feed/_like_button.html", {"post": post, "user": request.user}, request=request)
        return HttpResponse(html)
    return redirect("feed:post_detail", pk=post.id)


@login_required
@no_superadmin_required
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
                value = form.cleaned_data.get(field)
                if value:
                    setattr(form.instance, field, value)
            if getattr(form, "_video_preview_key", None):
                form.instance.video_preview = form._video_preview_key
            form.save()
            if request.headers.get("HX-Request"):
                return HttpResponse(status=204, headers={"HX-Redirect": reverse("feed:post_detail", args=[post.pk])})
            messages.success(request, "Postagem atualizada com sucesso.")
            return redirect("feed:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post, user=request.user)

    return render(request, "feed/post_update.html", {"form": form, "post": post})


@login_required
@no_superadmin_required
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


# Moderação desativada: endpoint removido
