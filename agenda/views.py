import calendar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.models import UserType
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin, NoSuperadminMixin

from .forms import (
    BriefingEventoCreateForm,
    BriefingEventoForm,
    EventoForm,
    InscricaoEventoForm,
    MaterialDivulgacaoEventoForm,
    ParceriaEventoForm,
)
from .models import (
    BriefingEvento,
    Evento,
    EventoLog,
    FeedbackNota,
    Tarefa,
    TarefaLog,
    InscricaoEvento,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
)
from .tasks import notificar_briefing_status
from dashboard.services import check_achievements

User = get_user_model()


def _queryset_por_organizacao(request):
    qs = Evento.objects.prefetch_related("inscricoes").all()
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if user.user_type == UserType.ROOT:
        return qs
    nucleo_ids = list(user.nucleos.values_list("id", flat=True))
    filtro = Q(organizacao=user.organizacao)
    if nucleo_ids:
        filtro |= Q(nucleo__in=nucleo_ids)
    return qs.filter(filtro)


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
            _queryset_por_organizacao(request)
            .filter(data_inicio__date=dia)
            .select_related("organizacao")
            .prefetch_related("inscricoes")
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
        _queryset_por_organizacao(request)
        .filter(data_inicio__date=dia)
        .annotate(fim=F("data_fim"))
        .select_related("organizacao")
        .prefetch_related("inscricoes")
        .order_by("data_inicio")
    )

    return render(
        request,
        "agenda/_lista_eventos_dia.html",
        {"eventos": eventos, "dia": dia, "dia_iso": dia_iso},
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
        messages.success(self.request, _("Evento criado com sucesso."))
        response = super().form_valid(form)
        EventoLog.objects.create(
            evento=self.object,
            usuario=self.request.user,
            acao="evento_criado",
        )
        return response


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
        """Registra log comparando campos alterados."""

        old_obj = self.get_object()
        detalhes: dict[str, dict[str, Any]] = {}
        for field in form.changed_data:
            before = getattr(old_obj, field)
            after = form.cleaned_data.get(field)
            if before != after:
                detalhes[field] = {"antes": before, "depois": after}

        messages.success(self.request, _("Evento atualizado com sucesso."))  # pragma: no cover
        response = super().form_valid(form)  # pragma: no cover
        EventoLog.objects.create(
            evento=self.object,
            usuario=self.request.user,
            acao="evento_atualizado",
            detalhes=detalhes,
        )
        return response


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
        self.object = self.get_object()
        EventoLog.objects.create(
            evento=self.object,
            usuario=request.user,
            acao="evento_excluido",
            detalhes={"titulo": self.object.titulo},
        )
        messages.success(self.request, _("Evento removido."))  # pragma: no cover
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


class TarefaDetailView(LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, DetailView):
    model = Tarefa
    template_name = "agenda/tarefa_detail.html"

    def get_queryset(self):
        qs = Tarefa.objects.select_related("organizacao")
        user = self.request.user
        if user.user_type == UserType.ROOT:
            return qs
        nucleo_ids = list(user.nucleos.values_list("id", flat=True))
        filtro = Q(organizacao=user.organizacao)
        if nucleo_ids:
            filtro |= Q(nucleo__in=nucleo_ids)
        return qs.filter(filtro)


class EventoSubscribeView(LoginRequiredMixin, NoSuperadminMixin, View):
    """Inscreve ou remove o usuário do evento."""

    def post(self, request, pk):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        if request.user.user_type == UserType.ADMIN:
            messages.error(request, _("Administradores não podem se inscrever em eventos."))  # pragma: no cover
            return redirect("agenda:evento_detalhe", pk=pk)
        inscricao, created = InscricaoEvento.objects.get_or_create(user=request.user, evento=evento)
        if not created and inscricao.status != "cancelada":
            inscricao.cancelar_inscricao()
            messages.success(request, _("Inscrição cancelada."))  # pragma: no cover
        else:
            inscricao.confirmar_inscricao()
            messages.success(request, _("Inscrição realizada."))  # pragma: no cover
        return redirect("agenda:evento_detalhe", pk=pk)


class EventoRemoveInscritoView(LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, View):
    """Remove um inscrito do evento."""

    def post(self, request, pk, user_id):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        if (
            request.user.user_type in {UserType.ADMIN, UserType.COORDENADOR}
            and evento.organizacao != request.user.organizacao
        ):
            messages.error(request, _("Acesso negado."))  # pragma: no cover
            return redirect("agenda:calendario")
        inscrito = get_object_or_404(User, pk=user_id)
        InscricaoEvento.objects.filter(user=inscrito, evento=evento).delete()
        messages.success(request, _("Inscrito removido."))  # pragma: no cover
        return redirect("agenda:evento_editar", pk=pk)


class EventoFeedbackView(LoginRequiredMixin, View):
    """Registra feedback pós-evento."""

    def post(self, request, pk):
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
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
        EventoLog.objects.create(
            evento=evento,
            usuario=usuario,
            acao="avaliacao_registrada",
            detalhes={"nota": nota},
        )
        messages.success(request, _("Feedback registrado com sucesso."))
        return redirect("agenda:evento_detalhe", pk=pk)


def eventos_por_dia(request):
    """Compatível com reverse('agenda:eventos_por_dia') via ?dia=YYYY-MM-DD"""
    dia_iso = request.GET.get("dia")
    if not dia_iso:
        raise Http404("Parâmetro 'dia' ausente.")
    return lista_eventos(request, dia_iso)


@login_required
def evento_orcamento(request, pk: int):
    evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
    if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR}:
        return HttpResponseForbidden()
    if request.method == "POST":
        try:
            evento.orcamento_estimado = Decimal(request.POST.get("orcamento_estimado", 0))
            evento.valor_gasto = Decimal(request.POST.get("valor_gasto", 0))
            evento.save(update_fields=["orcamento_estimado", "valor_gasto", "updated_at"])
        except (TypeError, InvalidOperation):
            return HttpResponse(status=400)
    data = {"orcamento_estimado": evento.orcamento_estimado, "valor_gasto": evento.valor_gasto}
    return JsonResponse(data)


@login_required
def fila_espera(request, pk: int):
    evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
    inscritos = list(
        evento.inscricoes.filter(status="pendente")
        .order_by("posicao_espera")
        .values("user__username", "posicao_espera")
    )
    return JsonResponse({"fila": inscritos})


@login_required
def avaliar_parceria(request, pk: int):
    parceria = get_object_or_404(
        ParceriaEvento.objects.filter(
            Q(evento__organizacao=request.user.organizacao)
            | Q(evento__nucleo__in=request.user.nucleos.values_list("id", flat=True))
        ),
        pk=pk,
    )
    if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR}:
        return HttpResponseForbidden()
    if request.method == "POST" and parceria.avaliacao is None:
        try:
            parceria.avaliacao = int(request.POST.get("avaliacao"))
        except (TypeError, ValueError):
            return HttpResponse(status=400)
        parceria.comentario = request.POST.get("comentario", "")
        parceria.save(update_fields=["avaliacao", "comentario", "updated_at"])
    return JsonResponse({"avaliacao": parceria.avaliacao, "comentario": parceria.comentario})


@csrf_exempt
def checkin_inscricao(request, pk: int):
    """Valida o QRCode enviado e registra o check-in."""
    if request.method != "POST":
        return HttpResponse(status=405)
    inscricao = get_object_or_404(InscricaoEvento, pk=pk)
    codigo = request.POST.get("codigo")
    expected = f"inscricao:{inscricao.pk}:{int(inscricao.created_at.timestamp())}"
    if codigo != expected or inscricao.check_in_realizado_em:
        return HttpResponseForbidden("QR inválido ou já usado")
    inscricao.realizar_check_in()
    return JsonResponse({"check_in": inscricao.check_in_realizado_em})


class InscricaoEventoListView(LoginRequiredMixin, ListView):
    model = InscricaoEvento
    template_name = "agenda/inscricao_list.html"
    context_object_name = "inscricoes"

    def get_queryset(self):
        qs = InscricaoEvento.objects.select_related("user", "evento")
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(user__username__icontains=q) | Q(evento__titulo__icontains=q))
        return qs


class InscricaoEventoCreateView(LoginRequiredMixin, CreateView):
    model = InscricaoEvento
    form_class = InscricaoEventoForm
    template_name = "agenda/inscricao_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        check_achievements(self.request.user)
        return response


class MaterialDivulgacaoEventoListView(LoginRequiredMixin, ListView):
    model = MaterialDivulgacaoEvento
    template_name = "agenda/material_list.html"
    context_object_name = "materiais"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        qs = MaterialDivulgacaoEvento.objects.select_related("evento")
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        if user.user_type not in {UserType.ADMIN, UserType.COORDENADOR, UserType.ROOT}:
            qs = qs.filter(status="aprovado")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(titulo__icontains=q)
        return qs.order_by("id")


class MaterialDivulgacaoEventoCreateView(LoginRequiredMixin, CreateView):
    model = MaterialDivulgacaoEvento
    form_class = MaterialDivulgacaoEventoForm
    template_name = "agenda/material_form.html"


class ParceriaPermissionMixin(UserPassesTestMixin):
    def test_func(self) -> bool:  # pragma: no cover - simples
        return self.request.user.user_type in {
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.ROOT,
        }


class ParceriaEventoListView(LoginRequiredMixin, ParceriaPermissionMixin, ListView):
    model = ParceriaEvento
    template_name = "agenda/parceria_list.html"
    context_object_name = "parcerias"

    def get_queryset(self):
        user = self.request.user
        qs = ParceriaEvento.objects.select_related("evento", "empresa", "nucleo")
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        nucleo = self.request.GET.get("nucleo")
        if nucleo:
            qs = qs.filter(nucleo_id=nucleo)
        return qs.order_by("-data_inicio")


class ParceriaEventoCreateView(LoginRequiredMixin, ParceriaPermissionMixin, CreateView):
    model = ParceriaEvento
    form_class = ParceriaEventoForm
    template_name = "agenda/parceria_form.html"
    success_url = reverse_lazy("agenda:parceria_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if user.user_type != UserType.ROOT:
            form.fields["evento"].queryset = Evento.objects.filter(
                Q(organizacao=user.organizacao)
                | Q(nucleo__in=user.nucleos.values_list("id", flat=True))
            )
            form.fields["empresa"].queryset = form.fields["empresa"].queryset.filter(
                organizacao=user.organizacao
            )
            form.fields["nucleo"].queryset = user.nucleos
        return form

    def form_valid(self, form):
        evento = form.cleaned_data["evento"]
        user = self.request.user
        if user.user_type != UserType.ROOT and evento.organizacao != user.organizacao:
            form.add_error("evento", _("Evento de outra organização"))
            return self.form_invalid(form)
        return super().form_valid(form)


class ParceriaEventoUpdateView(LoginRequiredMixin, ParceriaPermissionMixin, UpdateView):
    model = ParceriaEvento
    form_class = ParceriaEventoForm
    template_name = "agenda/parceria_form.html"
    success_url = reverse_lazy("agenda:parceria_list")

    def get_queryset(self):
        qs = ParceriaEvento.objects.all()
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        return qs

    def get_form(self, form_class=None):
        return ParceriaEventoCreateView.get_form(self, form_class)

    def form_valid(self, form):
        """Registra alterações da parceria."""
        old_obj = self.get_object()
        detalhes: dict[str, dict[str, Any]] = {}
        for field in form.changed_data:
            before = getattr(old_obj, field)
            after = form.cleaned_data.get(field)
            if before != after:
                detalhes[field] = {"antes": before, "depois": after}
        response = super().form_valid(form)
        EventoLog.objects.create(
            evento=self.object.evento,
            usuario=self.request.user,
            acao="parceria_atualizada",
            detalhes=detalhes,
        )
        return response


class ParceriaEventoDeleteView(LoginRequiredMixin, ParceriaPermissionMixin, DeleteView):
    model = ParceriaEvento
    template_name = "agenda/parceria_confirm_delete.html"
    success_url = reverse_lazy("agenda:parceria_list")

    def get_queryset(self):
        qs = ParceriaEvento.objects.all()
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        return qs

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        self.object = self.get_object()
        EventoLog.objects.create(
            evento=self.object.evento,
            usuario=request.user,
            acao="parceria_excluida",
            detalhes={"empresa": str(self.object.empresa_id)},
        )
        return super().delete(request, *args, **kwargs)


class BriefingEventoListView(LoginRequiredMixin, ListView):
    model = BriefingEvento
    template_name = "agenda/briefing_list.html"
    context_object_name = "briefings"

    def get_queryset(self):
        user = self.request.user
        qs = BriefingEvento.objects.select_related("evento")
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(evento__titulo__icontains=q)
        return qs


class BriefingEventoCreateView(LoginRequiredMixin, CreateView):
    model = BriefingEvento
    form_class = BriefingEventoCreateForm
    template_name = "agenda/briefing_form.html"

    def form_valid(self, form):
        evento = form.cleaned_data.get("evento")
        if BriefingEvento.objects.filter(evento=evento, deleted=False).exists():
            form.add_error("evento", _("Já existe briefing para este evento."))
            return self.form_invalid(form)
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            if not (
                evento.organizacao == user.organizacao
                or (evento.nucleo_id and evento.nucleo_id in nucleo_ids)
            ):
                form.add_error("evento", _("Evento de outra organização ou núcleo"))
                return self.form_invalid(form)
        messages.success(self.request, _("Briefing criado com sucesso."))
        return super().form_valid(form)


class BriefingEventoUpdateView(LoginRequiredMixin, UpdateView):
    model = BriefingEvento
    form_class = BriefingEventoForm
    template_name = "agenda/briefing_form.html"

    def get_queryset(self):
        qs = BriefingEvento.objects.all()
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        return qs

    def form_valid(self, form):
        old_obj = self.get_object()
        detalhes: dict[str, dict[str, Any]] = {}
        for field in form.changed_data:
            before = getattr(old_obj, field)
            after = form.cleaned_data.get(field)
            if before != after:
                detalhes[field] = {"antes": before, "depois": after}
        response = super().form_valid(form)
        EventoLog.objects.create(
            evento=self.object.evento,
            usuario=self.request.user,
            acao="briefing_atualizado",
            detalhes=detalhes,
        )
        return response


class BriefingEventoStatusView(LoginRequiredMixin, View):
    """Atualiza o status do briefing registrando avaliador e timestamps."""

    def post(self, request, pk: int, status: str):
        if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR}:
            return HttpResponseForbidden()
        briefing = get_object_or_404(
            BriefingEvento.objects.filter(
                Q(evento__organizacao=request.user.organizacao)
                | Q(evento__nucleo__in=request.user.nucleos.values_list("id", flat=True))
            ),
            pk=pk,
        )
        now = timezone.now()
        update_fields = ["status", "avaliado_por", "avaliado_em", "updated_at"]
        briefing.avaliado_por = request.user
        briefing.avaliado_em = now
        detalhes = {}
        if status == "orcamentado":
            briefing.status = "orcamentado"
            briefing.orcamento_enviado_em = now
            briefing.prazo_limite_resposta = request.POST.get("prazo_limite_resposta") or briefing.prazo_limite_resposta
            update_fields.extend(["orcamento_enviado_em", "prazo_limite_resposta"])
        elif status == "aprovado":
            briefing.status = "aprovado"
            briefing.aprovado_em = now
            briefing.coordenadora_aprovou = True
            update_fields.extend(["aprovado_em", "coordenadora_aprovou"])
        elif status == "recusado":
            briefing.status = "recusado"
            briefing.recusado_em = now
            briefing.recusado_por = request.user
            briefing.motivo_recusa = request.POST.get("motivo_recusa", "")
            update_fields.extend(["recusado_em", "motivo_recusa", "recusado_por"])
            detalhes["motivo_recusa"] = briefing.motivo_recusa
        else:
            return HttpResponseBadRequest()
        briefing.save(update_fields=update_fields)
        EventoLog.objects.create(
            evento=briefing.evento,
            usuario=request.user,
            acao=f"briefing_{status}",
            detalhes=detalhes,
        )
        notificar_briefing_status.delay(briefing.pk, briefing.status)
        messages.success(request, _("Status do briefing atualizado."))
        return redirect("agenda:briefing_list")
