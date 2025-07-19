import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import UserType
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin, NoSuperadminMixin

from .forms import BriefingEventoForm, EventoForm, InscricaoEventoForm, MaterialDivulgacaoEventoForm
from .models import BriefingEvento, Evento, FeedbackNota, InscricaoEvento, MaterialDivulgacaoEvento

User = get_user_model()


def _queryset_por_organizacao(request):
    qs = Evento.objects.prefetch_related("inscricoes").all()
    if request.user.user_type == UserType.ADMIN:
        qs = qs.filter(organizacao=request.user.organizacao)
    return qs


def calendario(request, ano: int | None = None, mes: int | None = None):
    today = timezone.localdate()
    ano = int(ano or today.year)
    mes = int(mes or today.month)

    try:
        data_atual = date(ano, mes, 1)
    except ValueError as exc:  # pragma: no cover - parametros invalidos
        raise Http404("Data inválida") from exc

    cal = calendar.Calendar(calendar.SUNDAY)
    dias = []

    for dia in cal.itermonthdates(ano, mes):
        evs_dia = (
            Evento.objects.filter(data_inicio__date=dia).select_related("organizacao").prefetch_related("inscricoes")
        )
        dias.append(
            {
                "data": dia,
                "hoje": dia == today,
                "mes_atual": dia.month == mes,
                "eventos": evs_dia,
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
    return TemplateResponse(request, "agenda/calendario.html", context)


def lista_eventos(request, dia_iso):
    try:
        dia = date.fromisoformat(dia_iso)
    except ValueError as exc:  # pragma: no cover - parametros invalidos
        raise Http404("Data inválida") from exc

    eventos = (
        Evento.objects.filter(data_inicio__date=dia)
        .annotate(fim=F("data_fim"))
        .select_related("organizacao")
        .prefetch_related("inscricoes")
        .order_by("data_inicio")
    )

    return render(
        request,
        "agenda/_lista_eventos_dia.html",
        {"eventos": eventos, "dia_iso": dia_iso},
    )


class EventoCreateView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Evento
    form_class = EventoForm
    template_name = "agenda/create.html"
    success_url = reverse_lazy("agenda:calendario")

    permission_required = "agenda.add_evento"

    def dispatch(self, request, *args, **kwargs):
        if request.user.username == "root":
            raise PermissionDenied("Usuário root não pode criar eventos.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao  # Corrigido para usar 'organizacao' ao criar evento
        messages.success(self.request, "Evento criado com sucesso.")
        return super().form_valid(form)


class EventoUpdateView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    GerenteRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Evento
    form_class = EventoForm
    template_name = "agenda/update.html"
    success_url = reverse_lazy("agenda:calendario")

    permission_required = "agenda.change_evento"

    def get_queryset(self):  # pragma: no cover
        return _queryset_por_organizacao(self.request)

    def form_valid(self, form):  # pragma: no cover
        messages.success(self.request, "Evento atualizado com sucesso.")  # pragma: no cover
        return super().form_valid(form)  # pragma: no cover


class EventoDeleteView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    GerenteRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    model = Evento
    template_name = "agenda/delete.html"
    success_url = reverse_lazy("agenda:calendario")

    permission_required = "agenda.delete_evento"

    def get_queryset(self):  # pragma: no cover
        return _queryset_por_organizacao(self.request)

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        messages.success(self.request, "Evento removido.")  # pragma: no cover
        return super().delete(request, *args, **kwargs)  # pragma: no cover


class EventoDetailView(LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, DetailView):
    model = Evento
    template_name = "agenda/detail.html"

    def get_queryset(self):
        return (
            _queryset_por_organizacao(self.request)
            .select_related("organizacao")
            .prefetch_related("inscricoes", "feedbacks")
        )


class EventoSubscribeView(LoginRequiredMixin, NoSuperadminMixin, View):
    """Inscreve ou remove o usuário do evento."""

    def post(self, request, pk):  # pragma: no cover
        evento = get_object_or_404(Evento, pk=pk)
        if request.user.user_type == UserType.ADMIN:
            messages.error(request, "Administradores não podem se inscrever em eventos.")  # pragma: no cover
            return redirect("agenda:evento_detalhe", pk=pk)
        inscricao, created = InscricaoEvento.objects.get_or_create(user=request.user, evento=evento)
        if not created and inscricao.status != "cancelada":
            inscricao.cancelar_inscricao()
            messages.success(request, "Inscrição cancelada.")  # pragma: no cover
        else:
            inscricao.confirmar_inscricao()
            messages.success(request, "Inscrição realizada.")  # pragma: no cover
        return redirect("agenda:evento_detalhe", pk=pk)


class EventoRemoveInscritoView(LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, View):
    """Remove um inscrito do evento."""

    def post(self, request, pk, user_id):  # pragma: no cover
        evento = get_object_or_404(Evento, pk=pk)
        if (
            request.user.user_type in {UserType.ADMIN, UserType.COORDENADOR}
            and evento.organizacao != request.user.organizacao
        ):
            messages.error(request, "Acesso negado.")  # pragma: no cover
            return redirect("agenda:calendario")
        inscrito = get_object_or_404(User, pk=user_id)
        InscricaoEvento.objects.filter(user=inscrito, evento=evento).delete()
        messages.success(request, "Inscrito removido.")  # pragma: no cover
        return redirect("agenda:evento_editar", pk=pk)


class EventoFeedbackView(LoginRequiredMixin, View):
    """Registra feedback pós-evento."""

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        usuario = request.user

        if not InscricaoEvento.objects.filter(user=usuario, evento=evento, status="confirmada").exists():
            return HttpResponseForbidden("Apenas inscritos podem enviar feedback.")

        if timezone.now() < evento.data_fim:
            return HttpResponseForbidden("Feedback só pode ser enviado após o evento.")

        try:
            nota = int(request.POST.get("nota"))
        except (TypeError, ValueError):
            return HttpResponseForbidden("Nota inválida.")

        if nota not in range(1, 6):
            return HttpResponseForbidden("Nota fora do intervalo permitido (1–5).")

        FeedbackNota.objects.update_or_create(
            evento=evento,
            usuario=usuario,
            defaults={
                "nota": nota,
                "comentario": request.POST.get("comentario", ""),
            },
        )

        messages.success(request, "Feedback registrado com sucesso.")
        return redirect("agenda:evento_detalhe", pk=pk)


def eventos_por_dia(request):
    """Compatível com reverse('agenda:eventos_por_dia') via ?dia=YYYY-MM-DD"""
    dia_iso = request.GET.get("dia")
    if not dia_iso:
        raise Http404("Parâmetro 'dia' ausente.")
    return lista_eventos(request, dia_iso)


class InscricaoEventoListView(LoginRequiredMixin, ListView):
    model = InscricaoEvento
    template_name = "agenda/inscricao_list.html"
    context_object_name = "inscricoes"

    def get_queryset(self):
        return InscricaoEvento.objects.select_related("user", "evento")


class InscricaoEventoCreateView(LoginRequiredMixin, CreateView):
    model = InscricaoEvento
    form_class = InscricaoEventoForm
    template_name = "agenda/inscricao_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class MaterialDivulgacaoEventoListView(LoginRequiredMixin, ListView):
    model = MaterialDivulgacaoEvento
    template_name = "agenda/material_list.html"
    context_object_name = "materiais"

    def get_queryset(self):
        return MaterialDivulgacaoEvento.objects.filter(ativo=True)


class MaterialDivulgacaoEventoCreateView(LoginRequiredMixin, CreateView):
    model = MaterialDivulgacaoEvento
    form_class = MaterialDivulgacaoEventoForm
    template_name = "agenda/material_form.html"


class BriefingEventoListView(LoginRequiredMixin, ListView):
    model = BriefingEvento
    template_name = "agenda/briefing_list.html"
    context_object_name = "briefings"


class BriefingEventoUpdateView(LoginRequiredMixin, UpdateView):
    model = BriefingEvento
    form_class = BriefingEventoForm
    template_name = "agenda/briefing_form.html"
