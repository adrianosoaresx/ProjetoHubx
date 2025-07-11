from datetime import date
import calendar

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from core.permissions import (
    AdminRequiredMixin,
    GerenteRequiredMixin,
    NoSuperadminMixin,
)

from .models import Evento
from .forms import EventoForm

User = get_user_model()


def calendario(request, ano=None, mes=None):
    today = date.today()
    ano = ano or today.year
    mes = mes or today.month
    cal = calendar.Calendar(calendar.SUNDAY)
    dias = []

    for dia in cal.itermonthdates(ano, mes):
        eventos = Evento.objects.filter(data_hora__date=dia)
        dias.append({
            "data": dia,
            "hoje": dia == today,
            "eventos": eventos,
        })

    context = {
        "dias_mes": dias,
        "data_atual": date(ano, mes, 1),
    }
    return render(request, "agenda/calendario.html", context)


def lista_eventos(request, dia_iso):
    eventos = list(Evento.objects.filter(data_hora__date=dia_iso).order_by("data_hora"))
    for ev in eventos:
        ev.fim = ev.data_hora + ev.duracao
    return render(
        request,
        "agenda/_lista_eventos_dia.html",
        {
            "eventos": eventos,
            "dia_iso": dia_iso,
        },
    )


class EventoCreateView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "agenda/create.html"
    success_url = reverse_lazy("agenda:calendario")

    def form_valid(self, form):
        if self.request.user.tipo_id == User.Tipo.ADMIN:
            form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, "Evento criado com sucesso.")
        return super().form_valid(form)


class EventoUpdateView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "agenda/update.html"
    success_url = reverse_lazy("agenda:calendario")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.tipo_id == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=self.request.user.organizacao)
        return qs

    def form_valid(self, form):
        messages.success(self.request, "Evento atualizado com sucesso.")
        return super().form_valid(form)


class EventoDeleteView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Evento
    template_name = "agenda/delete.html"
    success_url = reverse_lazy("agenda:calendario")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.tipo_id == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=self.request.user.organizacao)
        return qs

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Evento removido.")
        return super().delete(request, *args, **kwargs)


class EventoDetailView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, DetailView):
    model = Evento
    template_name = "agenda/detail.html"


class EventoSubscribeView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    """Inscreve ou remove o usuário do evento."""

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        if request.user.tipo_id == User.Tipo.ADMIN:
            messages.error(request, "Administradores não podem se inscrever em eventos.")
            return redirect("agenda:evento_detail", pk=pk)
        if request.user in evento.inscritos.all():
            evento.inscritos.remove(request.user)
            messages.success(request, "Inscrição cancelada.")
        else:
            evento.inscritos.add(request.user)
            messages.success(request, "Inscrição realizada.")
        return redirect("agenda:evento_detail", pk=pk)


class EventoRemoveInscritoView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    """Remove um inscrito do evento."""

    def post(self, request, pk, user_id):
        evento = get_object_or_404(Evento, pk=pk)
        if request.user.tipo_id in {User.Tipo.ADMIN, User.Tipo.GERENTE} and evento.organizacao != request.user.organizacao:
            messages.error(request, "Acesso negado.")
            return redirect("agenda:calendario")
        inscrito = get_object_or_404(User, pk=user_id)
        if inscrito in evento.inscritos.all():
            evento.inscritos.remove(inscrito)
            messages.success(request, "Inscrito removido.")
        return redirect("agenda:evento_update", pk=pk)
