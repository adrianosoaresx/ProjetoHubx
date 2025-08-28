from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from feed.models import Post


def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:perfil")
    return render(request, "core/home.html")


@login_required
def posts_highlights(request):
    posts = Post.objects.select_related("autor").order_by("-created_at")[:3]
    return render(request, "feed/_post_list.html", {"posts": posts})


class AboutView(TemplateView):
    template_name = "core/about.html"


class TermsView(TemplateView):
    template_name = "core/terms.html"


class PrivacyView(TemplateView):
    template_name = "core/privacy.html"
