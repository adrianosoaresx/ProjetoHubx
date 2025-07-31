from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.models import UserType
from core.permissions import AdminRequiredMixin, SuperadminRequiredMixin

from .forms import OrganizacaoForm
from .models import Organizacao

User = get_user_model()


class OrganizacaoListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = Organizacao
    template_name = "organizacoes/list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q")
        tipo = self.request.GET.get("tipo")
        cidade = self.request.GET.get("cidade")
        estado = self.request.GET.get("estado")
        order = self.request.GET.get("order", "nome")

        if query:
            qs = qs.filter(nome__icontains=query)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if cidade:
            qs = qs.filter(cidade__icontains=cidade)
        if estado:
            qs = qs.filter(estado__icontains=estado)

        allowed_order = {"nome", "tipo", "cidade", "estado", "created"}
        if order not in allowed_order:
            order = "nome"
        return qs.order_by(order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = Organizacao._meta.get_field("tipo").choices
        return context


class OrganizacaoCreateView(SuperadminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/create.html"
    success_url = reverse_lazy("organizacoes:list")

    def form_valid(self, form):
        messages.success(self.request, "Organização criada com sucesso.")
        return super().form_valid(form)


class OrganizacaoUpdateView(SuperadminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Organizacao
    form_class = OrganizacaoForm
    template_name = "organizacoes/update.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset()

    def form_valid(self, form):
        messages.success(self.request, "Organização atualizada com sucesso.")
        return super().form_valid(form)


class OrganizacaoDeleteView(SuperadminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Organizacao
    template_name = "organizacoes/delete.html"
    success_url = reverse_lazy("organizacoes:list")

    def get_queryset(self):
        return super().get_queryset()

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Organização removida.")
        return super().delete(request, *args, **kwargs)


class OrganizacaoDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    model = Organizacao
    template_name = "organizacoes/detail.html"

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("nucleos")
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(pk=getattr(user, "organizacao_id", None))
        return qs
