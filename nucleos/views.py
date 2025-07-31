from __future__ import annotations

import csv
import io

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from accounts.models import UserType
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin, NoSuperadminMixin

from .forms import (
    MembroRoleForm,
    NucleoForm,
    NucleoSearchForm,
    ParticipacaoDecisaoForm,
    SuplenteForm,
)
from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from .tasks import (
    notify_exportacao_membros,
    notify_participacao_aprovada,
    notify_participacao_recusada,
    notify_suplente_designado,
)

User = get_user_model()


class NucleoListView(NoSuperadminMixin, LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/list.html"
    paginate_by = 10

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user, participacoes__status="aprovado")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
        order_by = self.request.GET.get("order_by")
        if order_by:
            qs = qs.order_by(order_by)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        return ctx


class NucleoCreateView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/create.html"
    success_url = reverse_lazy("nucleos:list")

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, _("Núcleo criado com sucesso."))
        return super().form_valid(form)


class NucleoUpdateView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/update.html"
    success_url = reverse_lazy("nucleos:list")

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user, participacoes__status="aprovado")
        return qs

    def form_valid(self, form):
        messages.success(self.request, _("Núcleo atualizado com sucesso."))
        return super().form_valid(form)


class NucleoDeleteView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        nucleo.deleted = True
        nucleo.deleted_at = timezone.now()
        nucleo.save(update_fields=["deleted", "deleted_at"])
        messages.success(request, _("Núcleo removido."))
        return redirect("nucleos:list")


class NucleoDetailView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/detail.html"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user, participacoes__status="aprovado")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nucleo = self.object
        ctx["membros_aprovados"] = nucleo.participacoes.filter(status="aprovado")
        ctx["coordenadores"] = nucleo.participacoes.filter(status="aprovado", is_coordenador=True)
        if self.request.user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            ctx["membros_pendentes"] = nucleo.participacoes.filter(status="pendente")
            ctx["suplentes"] = nucleo.coordenadores_suplentes.all()
        return ctx


class ParticipacaoCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        ParticipacaoNucleo.objects.get_or_create(user=request.user, nucleo=nucleo)
        messages.success(request, _("Solicitação enviada."))
        return redirect("nucleos:detail", pk=pk)


class ParticipacaoDecisaoView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, FormView):
    form_class = ParticipacaoDecisaoForm

    def form_valid(self, form):
        nucleo = get_object_or_404(Nucleo, pk=self.kwargs["pk"])
        participacao = get_object_or_404(ParticipacaoNucleo, pk=self.kwargs["participacao_id"], nucleo=nucleo)
        if participacao.status != "pendente":
            return redirect("nucleos:detail", pk=nucleo.pk)
        participacao.decidido_por = self.request.user
        participacao.data_decisao = timezone.now()
        if form.cleaned_data["acao"] == "approve":
            participacao.status = "aprovado"
            participacao.save(update_fields=["status", "decidido_por", "data_decisao"])
            notify_participacao_aprovada.delay(participacao.id)
        else:
            participacao.status = "recusado"
            participacao.save(update_fields=["status", "decidido_por", "data_decisao"])
            notify_participacao_recusada.delay(participacao.id)
        return redirect("nucleos:detail", pk=nucleo.pk)


class MembroRemoveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        participacao.delete()
        messages.success(request, _("Membro removido do núcleo."))
        return redirect("nucleos:detail", pk=pk)


class MembroRoleView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        form = MembroRoleForm(request.POST, instance=participacao)
        if form.is_valid():
            form.save()
        return redirect("nucleos:detail", pk=pk)


class SuplenteCreateView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, CreateView):
    model = CoordenadorSuplente
    form_class = SuplenteForm
    template_name = "nucleos/suplente_form.html"

    def form_valid(self, form):
        nucleo = get_object_or_404(Nucleo, pk=self.kwargs["pk"])
        form.instance.nucleo = nucleo
        response = super().form_valid(form)
        notify_suplente_designado.delay(nucleo.id, form.instance.usuario.email)
        messages.success(self.request, _("Suplente adicionado."))
        return response

    def get_success_url(self):
        return reverse_lazy("nucleos:detail", kwargs={"pk": self.kwargs["pk"]})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pk"] = self.kwargs["pk"]
        return ctx


class SuplenteDeleteView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, suplente_id):
        nucleo = get_object_or_404(Nucleo, pk=pk)
        suplente = get_object_or_404(CoordenadorSuplente, pk=suplente_id, nucleo=nucleo)
        suplente.delete()
        messages.success(request, _("Suplente removido."))
        return redirect("nucleos:detail", pk=pk)


class ExportarMembrosView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk)
        participacoes = nucleo.participacoes.select_related("user")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Nome", "Email", "Status", "Função"])
        for p in participacoes:
            funcao = _("Coordenador") if p.is_coordenador else _("Membro")
            nome = p.user.get_full_name() or p.user.username
            writer.writerow([nome, p.user.email, p.status, funcao])
        notify_exportacao_membros.delay(nucleo.id)
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=nucleo-{nucleo.id}-membros.csv"
        return response
