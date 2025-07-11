from datetime import date
import calendar

from django.shortcuts import render

from eventos.models import Evento
from eventos.views import EventoDetailView


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
    return render(request, "agenda/_lista_eventos_dia.html", {
        "eventos": eventos,
        "dia_iso": dia_iso,
    })


# Reexport detail view for URL configuration
class EventoDetailProxyView(EventoDetailView):
    template_name = "eventos/detail.html"
