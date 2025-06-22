import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from .models import Evento
from .forms import EventoForm

User = get_user_model()


class EventoListView(GerenteRequiredMixin, LoginRequiredMixin, ListView):
    model = Evento
    template_name = "eventos/list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.tipo in {User.Tipo.ADMIN, User.Tipo.GERENTE}:
            queryset = queryset.filter(organizacao=user.organizacao)
        mes = self.request.GET.get("mes")
        ano = self.request.GET.get("ano")
        if mes and ano:
            queryset = queryset.filter(data_hora__month=mes, data_hora__year=ano)
        return queryset


class EventoCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/create.html"
    success_url = reverse_lazy("eventos:list")

    def form_valid(self, form):
        if self.request.user.tipo == User.Tipo.ADMIN:
            form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, "Evento criado com sucesso.")
        return super().form_valid(form)


class EventoUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/update.html"
    success_url = reverse_lazy("eventos:list")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.tipo == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=self.request.user.organizacao)
        return qs

    def form_valid(self, form):
        messages.success(self.request, "Evento atualizado com sucesso.")
        return super().form_valid(form)


class EventoDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Evento
    template_name = "eventos/delete.html"
    success_url = reverse_lazy("eventos:list")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.tipo == User.Tipo.ADMIN:
            qs = qs.filter(organizacao=self.request.user.organizacao)
        return qs

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Evento removido.")
        return super().delete(request, *args, **kwargs)


class EventoCalendarView(GerenteRequiredMixin, LoginRequiredMixin, ListView):
    model = Evento
    template_name = "eventos/calendar.html"

    def get_month_year(self):
        today = date.today()
        mes = int(self.request.GET.get("mes", today.month))
        ano = int(self.request.GET.get("ano", today.year))
        return mes, ano

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mes, ano = self.get_month_year()
        cal = calendar.Calendar()
        dias = cal.itermonthdates(ano, mes)
        eventos_por_dia = {}
        eventos = Evento.objects.filter(data_hora__year=ano, data_hora__month=mes)
        user = self.request.user
        if user.tipo in {User.Tipo.ADMIN, User.Tipo.GERENTE}:
            eventos = eventos.filter(organizacao=user.organizacao)
        for event in eventos:
            dia = event.data_hora.date()
            eventos_por_dia.setdefault(dia, []).append(event)
        context.update({
            "mes": mes,
            "ano": ano,
            "dias": dias,
            "eventos_por_dia": eventos_por_dia,
            "weekdays": "Seg Ter Qua Qui Sex Sab Dom".split(),
        })
        return context


class EventoDetailView(GerenteRequiredMixin, LoginRequiredMixin, DetailView):
    model = Evento
    template_name = "eventos/detail.html"


class EventoSubscribeView(GerenteRequiredMixin, LoginRequiredMixin, View):
    """Inscreve ou remove o usuário do evento."""

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        if request.user in evento.inscritos.all():
            evento.inscritos.remove(request.user)
            messages.success(request, "Inscrição cancelada.")
        else:
            evento.inscritos.add(request.user)
            messages.success(request, "Inscrição realizada.")
        return redirect("eventos:detail", pk=pk)
