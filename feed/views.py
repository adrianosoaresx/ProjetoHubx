from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.cache import cache
from django.db import connection
from django.db.models import BooleanField, Count, Exists, OuterRef, Q, Subquery, Value
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView
from django_ratelimit.core import is_ratelimited

from accounts.models import User, UserType
from eventos.models import Evento
from core.cache import get_cache_version
from core.permissions import NoSuperadminMixin, no_superadmin_required
from core.utils import get_back_navigation_fallback, resolve_back_href

# Moderação desativada: não é necessário notificar moderação
from nucleos.models import Nucleo
from nucleos.permissions import can_manage_feed
from organizacoes.models import Organizacao

from .api import _post_rate, _read_rate
from .forms import CommentForm, PostForm
from .utils import get_allowed_nucleos_for_user
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
            )
        )
        .order_by("-created_at")
        .distinct()
    )

    context = {
        "posts": posts,
        "nucleos_do_usuario": Nucleo.objects.filter(participacoes__user=request.user),
        "page_title": _("Meu Mural"),
        "hero_title": _("Meu Mural"),
        "hero_action_template": "feed/hero_actions_mural.html",
    }
    return render(request, "feed/mural.html", context)


def user_feed(request, username):
    """Exibe o mural público de um usuário."""

    perfil = get_object_or_404(User, username=username)
    if not perfil.perfil_publico and request.user != perfil:
        raise Http404

    posts = (
        Post.objects.select_related("autor", "organizacao", "nucleo", "evento")
        .prefetch_related("reacoes", "comments")
        .filter(deleted=False, autor=perfil)
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
        )
    )

    if request.user.is_authenticated:
        posts = posts.annotate(
            is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)),
            is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=request.user, deleted=False)),
            is_liked=Exists(
                Reacao.objects.filter(post=OuterRef("pk"), user=request.user, vote="like", deleted=False)
            ),
            is_shared=Exists(
                Reacao.objects.filter(post=OuterRef("pk"), user=request.user, vote="share", deleted=False)
            ),
        )
    else:
        posts = posts.annotate(
            is_bookmarked=Value(False, output_field=BooleanField()),
            is_flagged=Value(False, output_field=BooleanField()),
            is_liked=Value(False, output_field=BooleanField()),
            is_shared=Value(False, output_field=BooleanField()),
        )

    posts = posts.order_by("-created_at").distinct()
    context = {"posts": posts}
    template = "feed/_grid.html" if request.headers.get("HX-Request") else "feed/mural.html"
    return render(request, template, context)


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
    return render(
        request,
        "feed/bookmarks.html",
        {
            "posts": posts,
            "page_title": _("Meus Favoritos") + " | Hubx",
            "hero_title": _("Meus Favoritos"),
            "hero_action_template": "feed/hero_actions_bookmarks.html",
        },
    )


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
        qs = qs.filter(deleted=False).annotate(
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
        # Moderação desativada: usuários veem seus posts, feed global e núcleos autorizados
        can_view_nucleos = can_manage_feed(user)
        if not user.is_staff:
            if can_view_nucleos:
                allowed_nucleos = get_allowed_nucleos_for_user(user)
                qs = qs.filter(
                    Q(autor=user)
                    | Q(tipo_feed="global")
                    | Q(tipo_feed="nucleo", nucleo__in=allowed_nucleos)
                )
            else:
                qs = qs.filter(Q(autor=user) | Q(tipo_feed="global"))
        qs = qs.distinct()

        if organizacao_id:
            qs = qs.filter(organizacao_id=organizacao_id)

        if tipo_feed == "usuario":
            qs = qs.filter(Q(autor=user) | Q(tipo_feed="global", organizacao=user.organizacao))
        elif tipo_feed == "nucleo":
            nucleo_id = self.request.GET.get("nucleo")
            nucleo = Nucleo.objects.filter(id=nucleo_id).first()
            if not nucleo or not can_manage_feed(user, nucleo):
                return qs.none()
            qs = qs.filter(tipo_feed="nucleo", nucleo_id=nucleo_id)
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

        context.setdefault("page_title", _("Vitrine") + " | Hubx")
        context.setdefault("hero_title", _("Mural empresarial"))
        context.setdefault("hero_subtitle", _("Onde empresas se encontram para colaborar e crescer."))
        context.setdefault("hero_action_template", "feed/hero_actions.html")

        tipo_feed = self.request.GET.get("tipo_feed")
        nova_postagem_params = {"back": "feed"}

        if tipo_feed == "nucleo":
            nucleo_id = self.request.GET.get("nucleo")
            nucleo = get_object_or_404(Nucleo, id=nucleo_id)
            if not can_manage_feed(user, nucleo):
                raise Http404

            context["nucleo"] = nucleo
            context["hero_title"] = _("Mural Núcleo %(nome)s") % {"nome": nucleo.nome}
            context["hero_subtitle"] = _("Mural empresarial do núcleo %(nome)s") % {
                "nome": nucleo.nome
            }
            nova_postagem_params.update({"tipo_feed": "nucleo", "nucleo": str(nucleo.pk)})

        context["nova_postagem_url"] = f"{reverse('feed:nova_postagem')}?{urlencode(nova_postagem_params)}"

        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request"):
            return render(self.request, "feed/_grid.html", context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)


class NovaPostagemView(LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "feed/post_form.html"
    success_url = reverse_lazy("feed:meu_mural")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.locked_nucleo: Nucleo | None = self._resolve_locked_nucleo()

    def _get_locked_feed_context(self) -> tuple[str | None, Nucleo | None, str | None]:
        """Retorna o contexto de feed travado, se houver.

        Quando o núcleo foi fixado via query string (``tipo_feed=nucleo`` e
        ``nucleo=<id>``), o usuário não pode alterar o tipo de feed durante a
        criação da postagem. Este helper consolida essa informação para ser
        reutilizada nas etapas de inicialização do formulário, renderização do
        contexto e validação.
        """

        locked_nucleo = getattr(self, "locked_nucleo", None)
        if locked_nucleo:
            return "nucleo", locked_nucleo, str(locked_nucleo.pk)

        return None, None, None

    def _get_back_origin(self) -> str:
        return (self.request.GET.get("back") or self.request.POST.get("back") or "").strip()

    def _get_back_fallback_map(self) -> dict[str, str]:
        return {
            "feed": reverse("feed:listar"),
            "minhas-postagens": f"{reverse('accounts:perfil')}#perfil-posts-accordion",
        }

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

    def _resolve_locked_nucleo(self) -> Nucleo | None:
        tipo_feed = (self.request.GET.get("tipo_feed") or "").strip()
        if tipo_feed != "nucleo":
            return None

        nucleo_id = (self.request.GET.get("nucleo") or "").strip()
        nucleo = get_object_or_404(Nucleo, id=nucleo_id)
        if not can_manage_feed(self.request.user, nucleo):
            raise Http404
        return nucleo

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        locked_tipo, locked_nucleo, _locked_nucleo_id = self._get_locked_feed_context()
        data = kwargs.get("data")
        is_bound_request = self.request.method == "POST" or data is not None
        mutable_data = data.copy() if data is not None else None
        user_org_id = getattr(self.request.user, "organizacao_id", None)
        if is_bound_request:
            if mutable_data is None:
                mutable_data = self.request.POST.copy()
            if user_org_id and not mutable_data.get("organizacao"):
                mutable_data.setdefault("organizacao", str(user_org_id))
            if self.locked_nucleo:
                mutable_data["tipo_feed"] = "nucleo"
                mutable_data["nucleo"] = str(self.locked_nucleo.pk)
        if self.locked_nucleo:
            kwargs.setdefault("initial", {})
            kwargs["initial"].update({"tipo_feed": "nucleo", "nucleo": self.locked_nucleo})
        elif locked_tipo:
            initial = kwargs.setdefault("initial", {})
            initial.setdefault("tipo_feed", locked_tipo)
            if locked_nucleo:
                initial.setdefault("nucleo", locked_nucleo)
        if mutable_data is not None:
            kwargs["data"] = mutable_data
        if self.request.FILES:
            files = self.request.FILES.copy()
            arquivo = files.get("arquivo")
            if arquivo:
                content_type = getattr(arquivo, "content_type", "") or ""
                name = getattr(arquivo, "name", "") or ""
                if content_type == "application/pdf" or name.lower().endswith(".pdf"):
                    files["pdf"] = arquivo
                elif content_type.startswith("video/"):
                    files["video"] = arquivo
                else:
                    files["image"] = arquivo
            kwargs["files"] = files
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        locked_tipo, locked_nucleo, _locked_nucleo_id = self._get_locked_feed_context()
        if locked_tipo:
            initial.setdefault("tipo_feed", locked_tipo)
            if locked_nucleo:
                initial.setdefault("nucleo", locked_nucleo)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        locked_tipo, locked_nucleo, locked_nucleo_id = self._get_locked_feed_context()
        context["nucleos_do_usuario"] = Nucleo.objects.filter(participacoes__user=self.request.user)
        context["tags_disponiveis"] = Tag.objects.all()
        locked_nucleo = self.locked_nucleo
        if locked_nucleo:
            selected_tipo = "nucleo"
            selected_nucleo = str(locked_nucleo.pk)
        else:
            # Seleção segura para o template (evita lookup direto em request.POST)
            selected_tipo = (
                self.request.POST.get("tipo_feed") or self.request.GET.get("tipo_feed") or "global"
            ).strip()
            selected_nucleo = (self.request.POST.get("nucleo") or self.request.GET.get("nucleo") or "").strip()
        context["selected_tipo_feed"] = selected_tipo
        context["selected_nucleo"] = selected_nucleo
        context["locked_nucleo"] = locked_nucleo
        context["tags_text_value"] = (self.request.POST.get("tags_text", "") or "").strip()
        form = context.get("form")
        context["link_preview_data"] = getattr(form, "link_preview_data", {}) if form else {}
        back_origin = self._get_back_origin()
        fallback_map = self._get_back_fallback_map()
        explicit_fallback = fallback_map.get(back_origin)
        default_fallback = reverse("feed:listar")
        fallback_url = get_back_navigation_fallback(
            self.request, fallback=explicit_fallback or default_fallback
        )
        if explicit_fallback:
            back_href = fallback_url
        else:
            back_href = resolve_back_href(self.request, fallback=fallback_url)
        context["back_href"] = back_href
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        context["cancel_component_config"] = {
            "href": back_href,
            "fallback_href": fallback_url,
        }
        form_action = reverse("feed:nova_postagem")
        query_string = self.request.META.get("QUERY_STRING", "")
        if query_string:
            form_action = f"{form_action}?{query_string}"
        context.update(
            {
                "is_update": False,
                "form_action": form_action,
                "hx_post_url": form_action,
                "hx_target": "#nova-postagem-form",
                "hx_swap": "outerHTML",
                "form_wrapper_id": "nova-postagem-form",
            }
        )
        context.update(
            {
                "lock_tipo_feed": bool(locked_tipo),
                "locked_tipo_feed": locked_tipo,
                "locked_nucleo": locked_nucleo,
            }
        )
        return context

    def form_valid(self, form):
        if self.locked_nucleo:
            form.cleaned_data["tipo_feed"] = "nucleo"
            form.cleaned_data["nucleo"] = self.locked_nucleo
            form.instance.tipo_feed = "nucleo"
            form.instance.nucleo = self.locked_nucleo
        tipo_feed = form.cleaned_data.get("tipo_feed")
        nucleo = form.cleaned_data.get("nucleo")
        if self.locked_nucleo and nucleo != self.locked_nucleo:
            return HttpResponseForbidden()
        tipo_feed = form.cleaned_data.get("tipo_feed")
        nucleo = form.cleaned_data.get("nucleo")
        if tipo_feed == "nucleo" and (not nucleo or not can_manage_feed(self.request.user, nucleo)):
            return HttpResponseForbidden()
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
                tags_objs = []
                for name in tag_names:
                    tag, _created = Tag.objects.get_or_create(nome=name, deleted=False)
                    tags_objs.append(tag)
                self.object.tags.set(tags_objs)
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

    def get_success_url(self):
        if self.locked_nucleo:
            nucleo_id = self.locked_nucleo.pk
        elif getattr(self, "object", None) and self.object.tipo_feed == "nucleo" and self.object.nucleo:
            nucleo_id = self.object.nucleo.pk
        else:
            nucleo_id = None

        if nucleo_id:
            query_string = urlencode({"tipo_feed": "nucleo", "nucleo": str(nucleo_id)})
            return f"{reverse('feed:listar')}?{query_string}"

        back_origin = self._get_back_origin()
        fallback_map = self._get_back_fallback_map()
        return fallback_map.get(back_origin) or super().get_success_url()

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
        qs = qs.filter(deleted=False).annotate(
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
            is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=self.request.user, deleted=False)),
            is_flagged=Exists(Flag.objects.filter(post=OuterRef("pk"), user=self.request.user, deleted=False)),
            is_liked=Exists(
                Reacao.objects.filter(post=OuterRef("pk"), user=self.request.user, vote="like", deleted=False)
            ),
            is_shared=Exists(
                Reacao.objects.filter(post=OuterRef("pk"), user=self.request.user, vote="share", deleted=False)
            ),
        )
        if not self.request.user.is_staff:
            if can_manage_feed(self.request.user):
                allowed_nucleos = get_allowed_nucleos_for_user(self.request.user)
                qs = qs.filter(
                    Q(autor=self.request.user)
                    | Q(tipo_feed="global")
                    | Q(tipo_feed="nucleo", nucleo__in=allowed_nucleos)
                )
            else:
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
    if post.tipo_feed == "nucleo" and not can_manage_feed(request.user, post.nucleo):
        if request.headers.get("HX-Request"):
            return HttpResponseForbidden()
        messages.error(request, "Você não tem permissão para editar esta postagem.")
        return redirect("feed:post_detail", pk=pk)
    if request.user != post.autor and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        if request.headers.get("HX-Request"):
            return HttpResponseForbidden()
        messages.error(request, "Você não tem permissão para editar esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    if request.method == "POST":
        files = request.FILES.copy() if request.FILES else request.FILES
        if files:
            arquivo = files.get("arquivo")
            if arquivo:
                content_type = getattr(arquivo, "content_type", "") or ""
                name = getattr(arquivo, "name", "") or ""
                if content_type == "application/pdf" or name.lower().endswith(".pdf"):
                    files["pdf"] = arquivo
                elif content_type.startswith("video/"):
                    files["video"] = arquivo
                else:
                    files["image"] = arquivo
        data = request.POST.copy()
        if not data.get("organizacao") and post.organizacao_id:
            data.setdefault("organizacao", str(post.organizacao_id))
        form = PostForm(data, files, instance=post, user=request.user)
        if form.is_valid():
            target_nucleo = form.cleaned_data.get("nucleo")
            target_tipo = form.cleaned_data.get("tipo_feed")
            if target_tipo == "nucleo" and not can_manage_feed(request.user, target_nucleo):
                if request.headers.get("HX-Request"):
                    return HttpResponseForbidden()
                messages.error(request, "Você não tem permissão para editar esta postagem.")
                return redirect("feed:post_detail", pk=pk)
            for field in ["image", "pdf", "video"]:
                value = form.cleaned_data.get(field)
                if value:
                    setattr(form.instance, field, value)
            if getattr(form, "_video_preview_key", None):
                form.instance.video_preview = form._video_preview_key
            form.save()
            tags_text_raw = (data.get("tags_text", "") or "").strip()
            if tags_text_raw:
                tag_names = [t.strip() for t in tags_text_raw.split(",") if t.strip()]
                if tag_names:
                    tags_objs = []
                    for name in tag_names:
                        tag, _created = Tag.objects.get_or_create(nome=name, deleted=False)
                        tags_objs.append(tag)
                    form.instance.tags.set(tags_objs)
                else:
                    form.instance.tags.clear()
            else:
                form.instance.tags.clear()
            if request.headers.get("HX-Request"):
                return HttpResponse(status=204, headers={"HX-Redirect": reverse("feed:post_detail", args=[post.pk])})
            messages.success(request, "Postagem atualizada com sucesso.")
            return redirect("feed:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post, user=request.user)

    back_origin = (request.GET.get("back") or request.POST.get("back") or "").strip()
    focus_post_id = (request.GET.get("focus") or request.POST.get("focus") or "").strip() or str(post.pk)

    back_fallback_map = {
        "minhas-postagens": f"{reverse('accounts:perfil')}#post-{focus_post_id}",
    }

    fallback_url = get_back_navigation_fallback(
        request,
        fallback=back_fallback_map.get(back_origin) or reverse("feed:post_detail", args=[post.pk]),
    )
    back_href = resolve_back_href(request, fallback=fallback_url)
    form_action = reverse("feed:post_update", args=[post.pk])
    context = {
        "form": form,
        "post": post,
        "back_href": back_href,
        "back_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
        "cancel_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar edição"),
        },
        "is_update": True,
        "form_action": form_action,
        "hx_post_url": form_action,
        "form_wrapper_id": None,
        "hx_target": None,
        "hx_swap": None,
        "selected_tipo_feed": request.POST.get("tipo_feed") or form.initial.get("tipo_feed") or form.instance.tipo_feed,
        "tags_text_value": request.POST.get("tags_text")
        or ", ".join(post.tags.order_by("nome").values_list("nome", flat=True)),
        "tags_disponiveis": Tag.objects.all(),
        "nucleos_do_usuario": Nucleo.objects.filter(participacoes__user=request.user),
        "link_preview_data": form.link_preview_data,
    }
    return render(request, "feed/post_form.html", context)


@login_required
@no_superadmin_required
def post_delete(request, pk):
    post = get_object_or_404(Post.objects.filter(deleted=False), pk=pk)
    if request.user != post.autor and request.user.user_type not in {UserType.ROOT, UserType.ADMIN}:
        if request.headers.get("HX-Request"):
            return HttpResponseForbidden()
        messages.error(request, "Você não tem permissão para remover esta postagem.")
        return redirect("feed:post_detail", pk=pk)

    form_action = reverse("feed:post_delete", args=[post.pk])
    is_htmx = bool(request.headers.get("HX-Request"))

    if request.method == "POST":
        post.soft_delete()
        if is_htmx:
            return HttpResponse(status=204, headers={"HX-Redirect": reverse("feed:listar")})
        messages.success(request, "Postagem removida.")
        return redirect("feed:listar")

    if is_htmx:
        modal_context = {
            "post": post,
            "titulo": _("Remover Postagem"),
            "mensagem": _("Tem certeza que deseja remover esta postagem?"),
            "submit_label": _("Remover"),
            "form_action": form_action,
        }
        return render(request, "feed/partials/post_delete_modal.html", modal_context)

    fallback_url = reverse("feed:post_detail", args=[post.pk])
    back_href = resolve_back_href(request, fallback=fallback_url)
    context = {
        "post": post,
        "back_href": back_href,
        "back_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
        },
        "cancel_component_config": {
            "href": back_href,
            "fallback_href": fallback_url,
            "aria_label": _("Cancelar exclusão"),
        },
    }
    return render(request, "feed/post_delete.html", context)


# Moderação desativada: endpoint removido
