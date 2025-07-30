from django.shortcuts import render
from django.views.generic import TemplateView


def home(request):
    return render(request, "core/home.html")


class AboutView(TemplateView):
    template_name = "core/about.html"


class TermsView(TemplateView):
    template_name = "core/terms.html"


class PrivacyView(TemplateView):
    template_name = "core/privacy.html"
