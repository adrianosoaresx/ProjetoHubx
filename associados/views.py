from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from core.permissions import AdminRequiredMixin, NoSuperadminMixin
from accounts.models import UserType


class AssociadoListView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "associados/lista.html"
    context_object_name = "associados"
    paginate_by = 10

    def get_queryset(self):
        User = get_user_model()
        qs = User.objects.filter(
            Q(is_associado=True) | Q(user_type=UserType.ASSOCIADO)
        ).select_related("organizacao", "nucleo")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        return qs.order_by("username")
