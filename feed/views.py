from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Post
from .forms import PostForm


@login_required
def meu_mural(request):
    posts = Post.objects.filter(autor=request.user)
    return render(request, "feed/mural.html", {"posts": posts})


class FeedListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "feed/feed.html"
    context_object_name = "posts"

    def get_queryset(self):
        qs = Post.objects.select_related("autor").order_by("-criado_em")
        filtro = self.request.GET.get("tipo", "publico")

        if filtro == Post.PUBLICO:
            return qs.filter(tipo_feed=Post.PUBLICO)

        if filtro == Post.NUCLEO:
            nucleos_ids = self.request.user.nucleos.values_list("id", flat=True)
            return qs.filter(tipo_feed=Post.NUCLEO, nucleo_id__in=nucleos_ids)

        return qs.filter(tipo_feed=Post.PUBLICO)


class NovaPostagemView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "feed/nova_postagem.html"
    success_url = reverse_lazy("feed:meu_mural")

    def dispatch(self, request, *args, **kwargs):
        if request.user.tipo and request.user.tipo.descricao.lower() == "root":
            return HttpResponseForbidden("Usuário root não pode publicar no feed.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        return super().form_valid(form)


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
