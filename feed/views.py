from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from accounts.models import UserType
from nucleos.models import Nucleo

from .forms import CommentForm, LikeForm, PostForm
from .models import Like, Post


@login_required
def meu_mural(request):
    """Exibe o mural pessoal do usuário com seus posts e posts globais."""

    posts = (
        Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
        .prefetch_related("likes", "comments")
        .filter(Q(autor=request.user) | Q(tipo_feed="global", organizacao=request.user.organizacao))
        .order_by("-created_at")
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

    def get_queryset(self):
        tipo_feed = self.request.GET.get("tipo_feed", "global")
        q = self.request.GET.get("q", "").strip()
        user = self.request.user

        qs = Post.objects.select_related("autor", "organizacao", "nucleo", "evento").prefetch_related(
            "likes", "comments"
        )

        if tipo_feed == "usuario":
            qs = qs.filter(Q(autor=user) | Q(tipo_feed="global", organizacao=user.organizacao))
        elif tipo_feed == "nucleo":
            nucleo_id = self.request.GET.get("nucleo")
            qs = qs.filter(tipo_feed="nucleo", nucleo_id=nucleo_id)
            if not user.nucleos.filter(id=nucleo_id).exists():
                qs = qs.none()
        elif tipo_feed == "evento":
            evento_id = self.request.GET.get("evento")
            qs = qs.filter(tipo_feed="evento", evento_id=evento_id)
        else:  # global
            qs = qs.filter(tipo_feed="global")
            if user.user_type != UserType.ROOT:
                qs = qs.filter(organizacao=user.organizacao)

        if q:
            qs = qs.filter(conteudo__icontains=q)

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
            else:
                files["image"] = file
            kwargs["files"] = files
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nucleos_do_usuario"] = Nucleo.objects.filter(participacoes__user=self.request.user)
        return context

    def form_valid(self, form):
        form.instance.autor = self.request.user
        form.instance.organizacao = self.request.user.organizacao
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Redirect": self.get_success_url()})
        return response


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = "feed/post_detail.html"
    context_object_name = "post"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = CommentForm()
        context["like_form"] = LikeForm()
        return context


@login_required
def create_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.post = post
        comment.save()
        return redirect("feed:post_detail", pk=post.id)
    return render(request, "feed/post_detail.html", {"post": post, "comment_form": form})


@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return redirect("feed:post_detail", pk=post.id)


@login_required
def post_update(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.autor and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        messages.error(request, "Você não tem permissão para editar esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        files = request.FILES
        file = request.FILES.get("arquivo")
        if file:
            files = request.FILES.copy()
            if file.content_type == "application/pdf" or file.name.lower().endswith(".pdf"):
                files["pdf"] = file
            else:
                files["image"] = file
        form = PostForm(request.POST, files, instance=post, user=request.user)
        if form.is_valid():
            form.instance.organizacao = request.user.organizacao
            form.save()
            messages.success(request, "Postagem atualizada com sucesso.")
            return redirect("feed:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post, user=request.user)

    return render(request, "feed/post_update.html", {"form": form, "post": post})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.autor and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        messages.error(request, "Você não tem permissão para remover esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        post.delete()
        messages.success(request, "Postagem removida.")
        return redirect("feed:listar")

    return render(request, "feed/post_delete.html", {"post": post})
