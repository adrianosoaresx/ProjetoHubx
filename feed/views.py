from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from .models import Post
from .forms import PostForm


@login_required
def meu_mural(request):
    posts = Post.objects.filter(autor=request.user)
    return render(request, "feed/mural.html", {"posts": posts})


@login_required
def feed_global(request):
    user = request.user
    posts = Post.objects.filter(
        Q(visibilidade=Post.Visibilidade.PUBLICO)
        | Q(
            visibilidade=Post.Visibilidade.CONEXOES,
            autor__connections=user,
        )
        | Q(autor=user)
    ).distinct()
    context = {
        "posts": posts,
        "user_can_moderate": request.user.tipo_id in (1, 2),
    }
    return render(request, "feed/feed.html", context)


@login_required
def nova_postagem(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.autor = request.user
            post.save()
            return redirect("feed:meu_mural")
    else:
        form = PostForm()
    return render(request, "feed/nova_postagem.html", {"form": form})


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    context = {
        "post": post,
        "user_can_moderate": request.user.tipo_id in (1, 2),
    }
    return render(request, "feed/post_detail.html", context)


@login_required
def post_update(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.autor and request.user.tipo_id not in (1, 2):
        messages.error(request, "Você não tem permissão para editar esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Postagem atualizada com sucesso.")
            return redirect("feed:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, "feed/post_update.html", {"form": form, "post": post})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.autor and request.user.tipo_id not in (1, 2):
        messages.error(request, "Você não tem permissão para remover esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        post.delete()
        messages.success(request, "Postagem removida.")
        return redirect("feed:feed")

    return render(request, "feed/post_delete.html", {"post": post})
