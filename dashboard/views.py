from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """View principal do painel administrativo."""

    template_name = "dashboard/admin_dashboard.html"
