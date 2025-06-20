from django import forms
from .models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            "organizacao",
            "titulo",
            "descricao",
            "data_hora",
            "duracao",
            "link_inscricao",
            "briefing",
            "inscritos",
        ]
        widgets = {
            "data_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "duracao": forms.TextInput(attrs={"placeholder": "HH:MM:SS"}),
            "inscritos": forms.SelectMultiple,
        }
