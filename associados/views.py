from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from accounts.models import UserType
from core.permissions import GerenteRequiredMixin, NoSuperadminMixin


class AssociadoListView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "associados/lista.html"
    context_object_name = "associados"
    paginate_by = 10

    def get_queryset(self):
        User = get_user_model()
        qs = (
            User.objects.filter(
                user_type=UserType.ASSOCIADO.value,
                organizacao=self.request.user.organizacao,
            )
            .select_related("organizacao", "nucleo")
        )
        # TODO: unify "user_type" and "is_associado" fields to avoid duplicate state
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs.order_by("username")
