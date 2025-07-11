from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .models import Post
from .forms import PostForm


@login_required
def meu_mural(request):
    posts = Post.objects.filter(autor=request.user)
    context = {
        "posts": posts,
        "nucleos_do_usuario": request.user.nucleos.all(),
    }
    return render(request, "feed/mural.html", context)


class FeedListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "feed/feed.html"
    context_object_name = "posts"
    paginate_by = 15

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        nucleo_id = self.request.GET.get("nucleo")
        qs = (
            Post.objects.select_related("autor", "nucleo")
            .order_by("-criado_em")
        )
        if nucleo_id:
            qs = qs.filter(nucleo_id=nucleo_id)
        else:
            qs = qs.filter(publico=True, nucleo__isnull=True)
        if q:
            qs = qs.filter(Q(conteudo__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nucleos_do_usuario"] = self.request.user.nucleos.all()
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
        if request.user.tipo and request.user.tipo.descricao.lower() == "root":
            return HttpResponseForbidden("Usuário root não pode publicar no feed.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        file = self.request.FILES.get("file")
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
        context["nucleos_do_usuario"] = self.request.user.nucleos.all()
        return context

    def form_valid(self, form):
        form.instance.autor = self.request.user
        destino = form.cleaned_data.get("destino")
        if destino == "publico":
            form.instance.tipo_feed = Post.PUBLICO
            form.instance.nucleo = None
            form.instance.publico = True
        else:
            form.instance.tipo_feed = Post.NUCLEO
            form.instance.nucleo_id = destino
            form.instance.publico = False
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
        files = request.FILES
        file = request.FILES.get("file")
        if file:
            files = request.FILES.copy()
            if file.content_type == "application/pdf" or file.name.lower().endswith(".pdf"):
                files["pdf"] = file
            else:
                files["image"] = file
        form = PostForm(request.POST, files, instance=post, user=request.user)
        if form.is_valid():
            destino = form.cleaned_data.get("destino")
            if destino == "publico":
                post.tipo_feed = Post.PUBLICO
                post.nucleo = None
                post.publico = True
            else:
                post.tipo_feed = Post.NUCLEO
                post.nucleo_id = destino
                post.publico = False
            form.save()
            messages.success(request, "Postagem atualizada com sucesso.")
            return redirect("feed:post_detail", pk=post.pk)
    else:
        initial_destino = "publico" if post.tipo_feed == Post.PUBLICO else post.nucleo_id
        form = PostForm(instance=post, user=request.user, initial={"destino": initial_destino})

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
        return redirect("feed:listar")

    return render(request, "feed/post_delete.html", {"post": post})
