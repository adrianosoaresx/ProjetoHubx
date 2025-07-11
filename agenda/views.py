from datetime import date, timedelta
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
from django.http import Http404
from django.views import View
from core.permissions import (
    AdminRequiredMixin,
    GerenteRequiredMixin,
    NoSuperadminMixin,
)

from .models import Evento
from .forms import EventoForm

User = get_user_model()


def calendario(request, ano: int | None = None, mes: int | None = None):
    today = date.today()
    ano = int(ano or today.year)
    mes = int(mes or today.month)

    try:
        data_atual = date(ano, mes, 1)
    except ValueError as exc:  # pragma: no cover - parametros invalidos
        raise Http404("Data inválida") from exc

    cal = calendar.Calendar(calendar.SUNDAY)
    dias = []

    for dia in cal.itermonthdates(ano, mes):
        eventos = Evento.objects.filter(data_hora__date=dia)
        dias.append(
            {
                "data": dia,
                "hoje": dia == today,
                "mes_atual": dia.month == mes,
                "eventos": eventos,
            }
        )

    prev_month = (data_atual - timedelta(days=1)).replace(day=1)
    next_month = (data_atual.replace(day=28) + timedelta(days=4)).replace(day=1)

    context = {
        "dias_mes": dias,
        "data_atual": data_atual,
        "prev_ano": prev_month.year,
        "prev_mes": prev_month.month,
        "next_ano": next_month.year,
        "next_mes": next_month.month,
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
