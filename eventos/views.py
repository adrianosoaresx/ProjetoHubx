import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)

from .models import Evento
from .forms import EventoForm


class EventoListView(LoginRequiredMixin, ListView):
    model = Evento
    template_name = "eventos/list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        mes = self.request.GET.get("mes")
        ano = self.request.GET.get("ano")
        if mes and ano:
            queryset = queryset.filter(data_hora__month=mes, data_hora__year=ano)
        return queryset


class EventoCreateView(LoginRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/create.html"
    success_url = reverse_lazy("eventos:list")

    def form_valid(self, form):
        messages.success(self.request, "Evento criado com sucesso.")
        return super().form_valid(form)


class EventoUpdateView(LoginRequiredMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/update.html"
    success_url = reverse_lazy("eventos:list")

    def form_valid(self, form):
        messages.success(self.request, "Evento atualizado com sucesso.")
        return super().form_valid(form)


class EventoDeleteView(LoginRequiredMixin, DeleteView):
    model = Evento
    template_name = "eventos/delete.html"
    success_url = reverse_lazy("eventos:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Evento removido.")
        return super().delete(request, *args, **kwargs)


class EventoCalendarView(LoginRequiredMixin, ListView):
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
        for event in Evento.objects.filter(data_hora__year=ano, data_hora__month=mes):
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


class EventoDetailView(LoginRequiredMixin, DetailView):
    model = Evento
    template_name = "eventos/detail.html"
