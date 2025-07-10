from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
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
