import calendar
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q, Count, Model
from django.db.models.fields.files import FieldFile
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import Promise
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import UserType
from core.permissions import (
    AdminOperatorOrCoordinatorRequiredMixin,
    AdminOrOperatorRequiredMixin,
    GerenteRequiredMixin,
    NoSuperadminMixin,
    no_superadmin_required,
)
from core.utils import resolve_back_href

from .forms import EventoForm, FeedbackForm, InscricaoEventoForm
from .models import Evento, EventoLog, FeedbackNota, InscricaoEvento
from .querysets import filter_eventos_por_usuario

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _queryset_por_organizacao(request):
    qs = Evento.objects.prefetch_related("inscricoes").all()
    return filter_eventos_por_usuario(qs, request.user)


def _get_tipo_usuario(user) -> str | None:
    tipo = getattr(user, "get_tipo_usuario", None)
    if isinstance(tipo, UserType):
        return tipo.value
    if hasattr(tipo, "value"):
        return tipo.value  # pragma: no cover - compatibilidade defensiva
    return tipo


def _usuario_eh_coordenador_do_evento(user, evento: Evento) -> bool:
    if evento.nucleo_id is None:
        return False
    participacoes = getattr(user, "participacoes", None)
    if participacoes is not None:
        if participacoes.filter(
            nucleo=evento.nucleo,
            papel="coordenador",
            status="ativo",
            status_suspensao=False,
        ).exists():
            return True
    return getattr(user, "nucleo_id", None) == evento.nucleo_id and getattr(user, "is_coordenador", False)


def _usuario_tem_acesso_restrito_evento(user, evento: Evento) -> bool:
    tipo_usuario = _get_tipo_usuario(user)
    if tipo_usuario in {UserType.ADMIN.value, UserType.OPERADOR.value}:
        return True
    if tipo_usuario != UserType.COORDENADOR.value:
        return False
    return _usuario_eh_coordenador_do_evento(user, evento)


def _usuario_pode_ver_inscritos(user, evento: Evento) -> bool:
    return _usuario_tem_acesso_restrito_evento(user, evento)


# ---------------------------------------------------------------------------
# List / Calendário
# ---------------------------------------------------------------------------


class EventoListView(LoginRequiredMixin, NoSuperadminMixin, ListView):
    template_name = "eventos/evento_list.html"
    context_object_name = "eventos"
    paginate_by = 12

    # ----- Querysets -----
    def get_base_queryset(self):
        if hasattr(self, "_base_queryset_cache"):
            return self._base_queryset_cache
        user = self.request.user
        qs = (
            Evento.objects.select_related("nucleo", "organizacao")
            .prefetch_related("inscricoes")
        )
        qs = filter_eventos_por_usuario(qs, user)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(titulo__icontains=q)
                | Q(descricao__icontains=q)
                | Q(nucleo__nome__icontains=q)
            )
        self._base_queryset_cache = qs
        return qs

    def get_queryset(self):
        qs = self.get_base_queryset()
        status_filter = self.request.GET.get("status")
        now = timezone.now()
        status_map = {"ativos": 0, "realizados": 1}
        if status_filter == "planejamento":
            qs = qs.filter(status=0, data_inicio__gt=now)
        elif status_filter == "cancelados":
            qs = qs.filter(status=2)
        elif status_filter in status_map:
            qs = qs.filter(status=status_map[status_filter])
        return qs.annotate(num_inscritos=Count("inscricoes", distinct=True)).order_by("-data_inicio")

    # ----- Contexto -----
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["title"] = _("Eventos")
        ctx["subtitle"] = None
        ctx["is_admin_org"] = user.get_tipo_usuario in {
            UserType.ADMIN.value,
            UserType.OPERADOR.value,
        }
        current_filter = self.request.GET.get("status") or ""
        if current_filter not in {"ativos", "realizados", "planejamento", "cancelados"}:
            current_filter = "todos"
        params = self.request.GET.copy()
        params.pop("page", None)

        def build_url(filter_value: str | None) -> str:
            query_params = params.copy()
            if filter_value in {"ativos", "realizados", "planejamento", "cancelados"}:
                query_params["status"] = filter_value
            else:
                query_params.pop("status", None)
            qstr = query_params.urlencode()
            return f"{self.request.path}?{qstr}" if qstr else self.request.path

        ctx["current_filter"] = current_filter
        ctx["planejamento_filter_url"] = build_url("planejamento")
        ctx["ativos_filter_url"] = build_url("ativos")
        ctx["realizados_filter_url"] = build_url("realizados")
        ctx["cancelados_filter_url"] = build_url("cancelados")
        ctx["todos_filter_url"] = build_url(None)
        ctx["is_planejamento_filter_active"] = current_filter == "planejamento"
        ctx["is_ativos_filter_active"] = current_filter == "ativos"
        ctx["is_realizados_filter_active"] = current_filter == "realizados"
        ctx["is_cancelados_filter_active"] = current_filter == "cancelados"

        base_qs = self.get_base_queryset()
        qs = self.get_queryset()
        now = timezone.now()
        ctx["total_eventos"] = base_qs.count()
        ctx["total_eventos_planejamento"] = base_qs.filter(status=0, data_inicio__gt=now).count()
        ctx["total_eventos_ativos"] = base_qs.filter(status=0).count()
        ctx["total_eventos_concluidos"] = base_qs.filter(status=1).count()
        ctx["total_eventos_cancelados"] = base_qs.filter(status=2).count()
        ctx["total_inscritos"] = InscricaoEvento.objects.filter(evento__in=qs).count()
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["querystring"] = urlencode(params, doseq=True)
        ctx.setdefault("object_list", ctx.get(self.context_object_name, []))
        ctx.setdefault("card_template", "_components/card_evento.html")
        ctx.setdefault("item_context_name", "evento")
        ctx.setdefault("empty_message", _("Nenhum evento encontrado."))
        return ctx


# ---------------------------------------------------------------------------
# Calendário e listagens auxiliares
# ---------------------------------------------------------------------------


@login_required
@no_superadmin_required
def calendario(request, ano: int | None = None, mes: int | None = None):
    if getattr(request.user, "user_type", None) == UserType.ROOT:
        return HttpResponseForbidden()
    hoje = timezone.localdate()
    if ano is None or mes is None:
        ano, mes = hoje.year, hoje.month
    try:
        primeiro_dia = date(ano, mes, 1)
    except ValueError as exc:
        raise Http404("Mês inválido") from exc
    cal = calendar.Calendar(firstweekday=0)
    dias_iterados = list(cal.itermonthdates(ano, mes))
    inicio_periodo, fim_periodo = dias_iterados[0], dias_iterados[-1]
    eventos_qs = (
        _queryset_por_organizacao(request)
        .filter(data_inicio__date__range=(inicio_periodo, fim_periodo))
        .select_related("organizacao")
        .prefetch_related("inscricoes")
        .order_by("data_inicio")
    )
    eventos_por_dia: dict[date, list[Evento]] = {}
    for ev in eventos_qs:
        d = timezone.localtime(ev.data_inicio).date()
        eventos_por_dia.setdefault(d, []).append(ev)
    dias_mes = [
        {"data": d, "mes_atual": d.month == mes, "hoje": d == hoje, "eventos": eventos_por_dia.get(d, [])}
        for d in dias_iterados
    ]
    prev_ano, prev_mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    next_ano, next_mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    dia_sel = hoje if (hoje.year, hoje.month) == (ano, mes) else primeiro_dia
    context = {
        "dias_mes": dias_mes,
        "data_atual": primeiro_dia,
        "prev_ano": prev_ano,
        "prev_mes": prev_mes,
        "next_ano": next_ano,
        "next_mes": next_mes,
        "dia": dia_sel,
        "eventos": eventos_por_dia.get(dia_sel, []),
        "title": _("Calendário mensal"),
        "subtitle": None,
    }
    return TemplateResponse(request, "eventos/calendario_mes.html", context)


@login_required
@no_superadmin_required
def calendario_cards_ultimos_30(request):
    if getattr(request.user, "user_type", None) == UserType.ROOT:
        return HttpResponseForbidden()
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=30)
    qs = (
        _queryset_por_organizacao(request)
        .filter(data_inicio__date__range=(inicio, hoje))
        .select_related("organizacao")
        .prefetch_related("inscricoes")
        .order_by("data_inicio")
    )
    agrupado: dict[date, list[Evento]] = {}
    for ev in qs:
        d = timezone.localtime(ev.data_inicio).date()
        agrupado.setdefault(d, []).append(ev)
    dias_com_eventos = [
        {"data": d, "eventos": evs} for d, evs in sorted(agrupado.items(), key=lambda x: x[0], reverse=True)
    ]
    context = {"dias_com_eventos": dias_com_eventos, "data_atual": hoje, "title": _("Eventos"), "subtitle": None}
    return TemplateResponse(request, "eventos/calendario.html", context)


@login_required
@no_superadmin_required
def lista_eventos(request, dia_iso: str):
    try:
        dia = date.fromisoformat(dia_iso)
    except ValueError:
        return HttpResponseBadRequest("Parâmetro 'dia' inválido.")
    if getattr(request.user, "user_type", None) == UserType.ROOT:
        return HttpResponseForbidden()
    eventos = (
        _queryset_por_organizacao(request)
        .filter(data_inicio__date=dia)
        .select_related("organizacao", "nucleo")
        .prefetch_related("inscricoes")
        .order_by("data_inicio")
    )
    context = {"dia": dia, "eventos": list(eventos), "title": _("Eventos"), "subtitle": None}
    return TemplateResponse(
        request,
        "eventos/partials/calendario/_lista_eventos_dia.html",
        context,
    )


@login_required
@no_superadmin_required
def painel_eventos(request):
    return calendario_cards_ultimos_30(request)


# ---------------------------------------------------------------------------
# CRUD Evento
# ---------------------------------------------------------------------------


class EventoCreateView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminOrOperatorRequiredMixin,
    CreateView,
):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/evento_form.html"
    success_url = reverse_lazy("eventos:calendario")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if _get_tipo_usuario(request.user) == UserType.ROOT.value:
            raise PermissionDenied("Usuário root não pode criar eventos.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "object" not in context:
            form = context.get("form")
            context["object"] = getattr(form, "instance", None)
        fallback_url = str(self.success_url)
        back_href = resolve_back_href(self.request, fallback=fallback_url)
        context.update(
            {
                "back_href": back_href,
                "title": _("Adicionar evento"),
                "subtitle": _("Cadastre novos eventos para a sua organização."),
            }
        )
        return context

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, _("Evento criado com sucesso."))
        response = super().form_valid(form)
        EventoLog.objects.create(evento=self.object, usuario=self.request.user, acao="evento_criado")
        return response


class EventoUpdateView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminOperatorOrCoordinatorRequiredMixin,
    UpdateView,
):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/evento_form.html"
    def get_form_kwargs(self):  # pragma: no cover
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_queryset(self):  # pragma: no cover
        return _queryset_por_organizacao(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.object
        fallback_url = reverse("eventos:calendario")
        back_href = resolve_back_href(self.request, fallback=fallback_url)
        context.update(
            {
                "back_href": back_href,
                "title": _("Editar Evento"),
                "subtitle": getattr(self.object, "descricao", None),
            }
        )
        return context

    def get_success_url(self):
        return reverse("eventos:evento_detalhe", kwargs={"pk": self.object.pk})

    def form_valid(self, form):  # pragma: no cover
        old_obj = self.get_object()
        detalhes: dict[str, dict[str, Any]] = {}

        def _serialize_value(value: Any) -> Any:
            if isinstance(value, Promise):
                return str(value)
            if isinstance(value, FieldFile):
                return value.name if value else None
            if isinstance(value, UploadedFile):
                return value.name
            if isinstance(value, Model):
                return {"id": value.pk, "repr": str(value)}
            if isinstance(value, dict):
                return {key: _serialize_value(val) for key, val in value.items()}
            if isinstance(value, (list, tuple, set)):
                return [_serialize_value(val) for val in value]
            return value

        for field in form.changed_data:
            before = getattr(old_obj, field)
            after = form.cleaned_data.get(field)
            if before != after:
                detalhes[field] = {"antes": _serialize_value(before), "depois": _serialize_value(after)}

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
    AdminOperatorOrCoordinatorRequiredMixin,
    DeleteView,
):
    model = Evento
    template_name = "eventos/delete.html"
    success_url = reverse_lazy("eventos:calendario")

    def get_queryset(self):  # pragma: no cover
        return _queryset_por_organizacao(self.request)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        is_htmx = bool(request.headers.get("HX-Request"))
        if is_htmx:
            context = {
                "evento": self.object,
                "titulo": _("Remover Evento"),
                "mensagem": format_html(
                    _("Tem certeza que deseja remover o evento <strong>{titulo}</strong>?"),
                    titulo=self.object.titulo,
                ),
                "submit_label": _("Remover"),
                "form_action": reverse("eventos:evento_excluir", args=[self.object.pk]),
            }
            return TemplateResponse(
                request,
                "eventos/partials/evento_delete_modal.html",
                context,
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.object
        context["title"] = _("Remover Evento")
        context["subtitle"] = getattr(self.object, "descricao", None)
        fallback = reverse("eventos:evento_detalhe", args=[self.object.pk])
        context["back_href"] = resolve_back_href(self.request, fallback=fallback)
        return context

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        self.object = self.get_object()
        EventoLog.objects.create(
            evento=self.object,
            usuario=request.user,
            acao="evento_excluido",
            detalhes={"titulo": self.object.titulo},
        )
        messages.success(self.request, _("Evento removido."))  # pragma: no cover
        response = super().delete(request, *args, **kwargs)  # pragma: no cover
        if bool(request.headers.get("HX-Request")):
            hx_response = HttpResponse(status=204)
            hx_response["HX-Redirect"] = str(self.get_success_url())
            return hx_response
        return response  # pragma: no cover


class EventoDetailView(LoginRequiredMixin, NoSuperadminMixin, DetailView):
    model = Evento
    template_name = "eventos/detail.html"

    def get_queryset(self):
        base = Evento.objects.select_related("organizacao").prefetch_related("inscricoes", "feedbacks")
        return filter_eventos_por_usuario(base, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        evento: Evento = self.object
        context["evento"] = evento
        minha_inscricao = (
            InscricaoEvento.objects.filter(
                evento=evento,
                user=user,
                status="confirmada",
                deleted=False,
            )
            .select_related("user")
            .first()
        )
        confirmada = bool(minha_inscricao)
        context["inscricao_confirmada"] = confirmada
        context["avaliacao_permitida"] = confirmada and timezone.now() > evento.data_fim
        context["inscricao"] = minha_inscricao
        context["inscricao_permitida"] = evento.status == Evento.Status.ATIVO
        context["back_href"] = self._resolve_back_href()
        if context["avaliacao_permitida"]:
            context["feedback_form"] = FeedbackForm()
        # Evita oferecer cancelamento quando o evento já começou
        context["pode_cancelar"] = (
            bool(minha_inscricao)
            and context["inscricao_permitida"]
            and timezone.now() < evento.data_inicio
        )
        inscricoes = list(
            InscricaoEvento.objects.filter(evento=evento, deleted=False)
            .select_related("user")
        )
        inscricoes_confirmadas = [inscricao for inscricao in inscricoes if inscricao.status == "confirmada"]
        status_counts = Counter(inscricao.status for inscricao in inscricoes)
        total_confirmadas = status_counts.get("confirmada", 0)
        total_pendentes = status_counts.get("pendente", 0)
        total_canceladas = status_counts.get("cancelada", 0)
        vagas_disponiveis = None
        if evento.participantes_maximo is not None:
            vagas_disponiveis = max(evento.participantes_maximo - total_confirmadas, 0)
        feedbacks = list(evento.feedbacks.all())
        total_feedbacks = len(feedbacks)
        media_feedback = None
        if total_feedbacks:
            media_feedback = sum(f.nota for f in feedbacks) / total_feedbacks
        tipo_usuario = _get_tipo_usuario(user)
        pode_editar_evento = user.has_perm("eventos.change_evento")
        pode_excluir_evento = user.has_perm("eventos.delete_evento")
        pode_gerenciar_inscricoes = tipo_usuario in {
            UserType.ADMIN.value,
            UserType.OPERADOR.value,
            UserType.COORDENADOR.value,
        }
        if tipo_usuario in {UserType.ADMIN.value, UserType.OPERADOR.value}:
            pode_editar_evento = True
            pode_excluir_evento = True
        context.update(
            {
                "local": evento.local,
                "cidade": evento.cidade,
                "estado": evento.estado,
                "cep": evento.cep,
                "participantes_maximo": evento.participantes_maximo,
                "orcamento_estimado": evento.orcamento_estimado,
                "valor_gasto": evento.valor_gasto,
                "inscricao_confirmada": confirmada,
                "total_inscricoes": len(inscricoes),
                "total_inscricoes_confirmadas": total_confirmadas,
                "total_inscricoes_pendentes": total_pendentes,
                "total_inscricoes_canceladas": total_canceladas,
                "total_presentes": evento.numero_presentes,
                "vagas_disponiveis": vagas_disponiveis,
                "media_feedback": media_feedback,
                "total_feedbacks": total_feedbacks,
                "inscricoes_confirmadas": inscricoes_confirmadas,
                "pode_editar_evento": pode_editar_evento,
                "pode_excluir_evento": pode_excluir_evento,
                "pode_gerenciar_inscricoes": pode_gerenciar_inscricoes,
                "pode_ver_campos_restritos": _usuario_tem_acesso_restrito_evento(user, evento),
            }
        )
        context["title"] = evento.titulo
        context["subtitle"] = getattr(evento, "descricao", None)
        context["pode_ver_inscritos"] = _usuario_pode_ver_inscritos(user, evento)
        return context

    def _resolve_back_href(self) -> str:
        request = self.request
        fallback = reverse("eventos:calendario")
        return resolve_back_href(request, fallback=fallback)


# ---------------------------------------------------------------------------
# Ações / Inscrições
# ---------------------------------------------------------------------------


class EventoInscricaoActionMixin:
    def _redirect(self, request, pk):
        redirect_url = reverse("eventos:evento_detalhe", args=[pk])
        if bool(request.headers.get("HX-Request")):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = redirect_url
            return response
        return redirect(redirect_url)


class EventoSubscribeView(EventoInscricaoActionMixin, LoginRequiredMixin, NoSuperadminMixin, View):
    def post(self, request, pk):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        if evento.status != Evento.Status.ATIVO:
            messages.error(
                request,
                _("Inscrições disponíveis apenas para eventos ativos."),
            )
            return self._redirect(request, pk)
        if _get_tipo_usuario(request.user) == UserType.ADMIN.value:
            messages.error(request, _("Administradores não podem se inscrever em eventos."))  # pragma: no cover
            return self._redirect(request, pk)
        inscricao, created = InscricaoEvento.all_objects.get_or_create(
            user=request.user,
            evento=evento,
        )

        if inscricao.deleted:
            update_fields = ["deleted", "deleted_at", "updated_at"]
            inscricao.deleted = False
            inscricao.deleted_at = None
            if inscricao.status == "cancelada":
                inscricao.status = "pendente"
                update_fields.append("status")
            inscricao.save(update_fields=update_fields)
        if inscricao.status == "confirmada":
            messages.info(request, _("Inscrição já confirmada."))
            return self._redirect(request, pk)
        try:
            inscricao.confirmar_inscricao()
        except ValueError as exc:
            if created:
                inscricao.delete()
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Inscrição realizada."))  # pragma: no cover
        return self._redirect(request, pk)


class EventoCancelSubscriptionView(EventoInscricaoActionMixin, LoginRequiredMixin, NoSuperadminMixin, View):
    def post(self, request, pk):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        if evento.status != Evento.Status.ATIVO:
            messages.error(
                request,
                _("Inscrições disponíveis apenas para eventos ativos."),
            )
            return self._redirect(request, pk)
        if _get_tipo_usuario(request.user) == UserType.ADMIN.value:
            messages.error(request, _("Administradores não podem cancelar inscrições."))
            return self._redirect(request, pk)

        try:
            inscricao = InscricaoEvento.objects.get(
                user=request.user,
                evento=evento,
            )
        except InscricaoEvento.DoesNotExist:
            if InscricaoEvento.all_objects.filter(
                user=request.user,
                evento=evento,
                deleted=True,
            ).exists():
                messages.info(request, _("Inscrição já cancelada."))
            else:
                messages.error(request, _("Nenhuma inscrição ativa encontrada."))
            return self._redirect(request, pk)

        if inscricao.status == "cancelada":
            messages.info(request, _("Inscrição já cancelada."))
            return self._redirect(request, pk)

        try:
            inscricao.cancelar_inscricao()
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Inscrição cancelada."))
        return self._redirect(request, pk)


class EventoCancelarInscricaoModalView(LoginRequiredMixin, NoSuperadminMixin, View):
    template_name = "eventos/partials/evento_cancelar_inscricao_modal.html"

    def get(self, request, pk):  # pragma: no cover - interface simples
        if request.headers.get("HX-Target") != "modal":
            return redirect("eventos:evento_detalhe", pk=pk)

        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)

        if _get_tipo_usuario(request.user) == UserType.ADMIN.value:
            return HttpResponseForbidden(_("Administradores não podem cancelar inscrições."))

        get_object_or_404(
            InscricaoEvento,
            user=request.user,
            evento=evento,
            status="confirmada",
        )

        context = {
            "evento": evento,
            "titulo": _("Cancelar inscrição"),
            "mensagem": _(
                "Tem certeza que deseja cancelar sua inscrição no evento %(evento)s?"
            )
            % {"evento": evento.titulo},
            "submit_label": _("Cancelar inscrição"),
            "form_action": reverse("eventos:evento_cancelar_inscricao", args=[evento.pk]),
        }

        return TemplateResponse(request, self.template_name, context)


class EventoRemoverInscritoModalView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminOperatorOrCoordinatorRequiredMixin,
    View,
):
    template_name = "eventos/partials/evento_remover_inscricao_modal.html"

    def get(self, request, pk, user_id):  # pragma: no cover - interface simples
        if request.headers.get("HX-Target") != "modal":
            return redirect("eventos:evento_detalhe", pk=pk)

        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        tipo_usuario = _get_tipo_usuario(request.user)
        if (
            tipo_usuario
            in {
                UserType.ADMIN.value,
                UserType.COORDENADOR.value,
                UserType.OPERADOR.value,
            }
            and evento.organizacao != getattr(request.user, "organizacao", None)
        ):
            return HttpResponseForbidden(_("Acesso negado."))

        inscrito = get_object_or_404(User, pk=user_id)
        get_object_or_404(
            InscricaoEvento,
            user=inscrito,
            evento=evento,
            deleted=False,
        )

        inscrito_nome = getattr(inscrito, "display_name", None) or inscrito.get_username()
        context = {
            "evento": evento,
            "titulo": _("Excluir inscrição"),
            "mensagem": _(
                "Tem certeza que deseja excluir a inscrição de %(inscrito)s no evento %(evento)s?"
            )
            % {"inscrito": inscrito_nome, "evento": evento.titulo},
            "submit_label": _("Excluir inscrição"),
            "cancel_label": _("Manter inscrição"),
            "form_action": reverse(
                "eventos:evento_remover_inscrito",
                args=[evento.pk, inscrito.pk],
            ),
        }

        return TemplateResponse(request, self.template_name, context)


class EventoRemoveInscritoView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminOperatorOrCoordinatorRequiredMixin,
    View,
):
    def post(self, request, pk, user_id):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        tipo_usuario = _get_tipo_usuario(request.user)
        if (
            tipo_usuario
            in {
                UserType.ADMIN.value,
                UserType.COORDENADOR.value,
                UserType.OPERADOR.value,
            }
            and evento.organizacao != request.user.organizacao
        ):
            messages.error(request, _("Acesso negado."))  # pragma: no cover
            return redirect("eventos:calendario")
        inscrito = get_object_or_404(User, pk=user_id)
        inscricao = get_object_or_404(InscricaoEvento, user=inscrito, evento=evento)
        inscricao.cancelar_inscricao()
        EventoLog.objects.create(
            evento=evento,
            usuario=request.user,
            acao="inscricao_removida",
            detalhes={"inscrito_id": inscrito.id},
        )
        messages.success(request, _("Inscrito removido."))  # pragma: no cover
        return redirect("eventos:evento_detalhe", pk=pk)


class InscricaoEventoUpdateView(
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminOperatorOrCoordinatorRequiredMixin,
    UpdateView,
):
    model = InscricaoEvento
    form_class = InscricaoEventoForm
    template_name = "eventos/inscricoes/inscricao_form.html"

    def get_queryset(self):
        eventos_qs = _queryset_por_organizacao(self.request)
        return (
            InscricaoEvento.objects.select_related("evento", "user")
            .filter(evento__in=eventos_qs)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = self.object.evento
        fallback = reverse("eventos:evento_detalhe", kwargs={"pk": evento.pk})
        context.update(
            {
                "evento": evento,
                "title": _("Editar inscrição"),
                "subtitle": getattr(evento, "descricao", None),
                "back_href": resolve_back_href(self.request, fallback=fallback),
            }
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Inscrição atualizada com sucesso."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "eventos:evento_detalhe", kwargs={"pk": self.object.evento.pk}
        )


class EventoFeedbackView(LoginRequiredMixin, NoSuperadminMixin, View):
    def get(self, request, pk):
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        usuario = request.user
        if not InscricaoEvento.objects.filter(user=usuario, evento=evento, status="confirmada").exists():
            return HttpResponseForbidden("Apenas inscritos podem enviar feedback.")
        if timezone.now() < evento.data_fim:
            return HttpResponseForbidden("Feedback só pode ser enviado após o evento.")
        fallback = reverse("eventos:evento_detalhe", kwargs={"pk": evento.pk})
        context = {
            "evento": evento,
            "title": _("Avaliar evento"),
            "subtitle": evento.descricao,
            "form": FeedbackForm(),
            "back_href": resolve_back_href(request, fallback=fallback),
        }
        return TemplateResponse(request, "eventos/avaliacao_form.html", context)

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
        if FeedbackNota.objects.filter(evento=evento, usuario=usuario).exists():
            return HttpResponseForbidden("Feedback já enviado.")
        FeedbackNota.objects.create(
            evento=evento,
            usuario=usuario,
            nota=nota,
            comentario=request.POST.get("comentario", ""),
        )
        EventoLog.objects.create(
            evento=evento,
            usuario=usuario,
            acao="avaliacao_registrada",
            detalhes={"nota": nota},
        )
        messages.success(request, _("Feedback registrado com sucesso."))
        return redirect("eventos:evento_detalhe", pk=pk)


# ---------------------------------------------------------------------------
# Listagem / criação de inscrições
# ---------------------------------------------------------------------------


class InscricaoEventoListView(LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, ListView):
    model = InscricaoEvento
    template_name = "eventos/inscricoes/inscricao_list.html"
    context_object_name = "inscricoes"

    def get_queryset(self):
        qs = InscricaoEvento.objects.select_related("user", "evento")
        qs = filter_eventos_por_usuario(qs, self.request.user, evento_field="evento")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(user__username__icontains=q) | Q(evento__titulo__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("title", _("Inscrições"))
        ev_id = self.request.GET.get("evento")
        if ev_id:
            try:
                context["evento"] = _queryset_por_organizacao(self.request).get(pk=ev_id)
                context["title"] = context["evento"].titulo
                fallback = reverse("eventos:evento_detalhe", kwargs={"pk": context["evento"].pk})
                context["back_href"] = resolve_back_href(self.request, fallback=fallback)
            except Evento.DoesNotExist:
                context["evento"] = None
        return context


class InscricaoEventoCreateView(LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = InscricaoEvento
    form_class = InscricaoEventoForm
    template_name = "eventos/inscricoes/inscricao_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.evento = get_object_or_404(_queryset_por_organizacao(request), pk=kwargs["pk"])
        if _get_tipo_usuario(request.user) == UserType.ADMIN.value:
            messages.error(request, _("Administradores não podem se inscrever em eventos."))
            return redirect("eventos:evento_detalhe", pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.evento
        context["title"] = self.evento.titulo
        fallback = reverse("eventos:evento_detalhe", kwargs={"pk": self.evento.pk})
        context["back_href"] = resolve_back_href(self.request, fallback=fallback)
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.evento = self.evento
        response = super().form_valid(form)
        self.object.confirmar_inscricao()
        messages.success(self.request, _("Inscrição realizada."))
        return response

    def get_success_url(self):
        return reverse_lazy("eventos:evento_detalhe", kwargs={"pk": self.evento.pk})


# ---------------------------------------------------------------------------
# Check-in de inscrições (reintroduzido após refatoração)
# ---------------------------------------------------------------------------


@login_required
@no_superadmin_required
def checkin_form(request, pk: int):
    """Exibe a página de check-in para uma inscrição específica.

    A URL usa o PK da inscrição. Validamos que o usuário pertence à mesma
    organização do evento. Permitimos acesso ao próprio inscrito ou a usuários
    de staff (ADMIN / COORDENADOR / GERENTE) da mesma organização. Outros
    recebem 403.
    """
    inscricao = get_object_or_404(InscricaoEvento.objects.select_related("evento", "user"), pk=pk)
    evento = inscricao.evento
    user = request.user
    # Verificação de organização
    if evento.organizacao != getattr(user, "organizacao", None):
        return HttpResponseForbidden()
    # Regras simples de permissão: o próprio usuário inscrito ou staff
    staff_tipos = {UserType.ADMIN.value, UserType.COORDENADOR.value}
    if hasattr(UserType, "GERENTE"):
        staff_tipos.add(UserType.GERENTE.value)
    if user != inscricao.user and _get_tipo_usuario(user) not in staff_tipos:
        return HttpResponseForbidden()
    context = {
        "evento": evento,
        "inscricao": inscricao,
        "title": _("Check-in do evento"),
        "subtitle": evento.descricao,
    }
    return TemplateResponse(request, "eventos/inscricoes/checkin_form.html", context)


@login_required
@no_superadmin_required
def checkin_inscricao(request, pk: int):
    """Endpoint API (POST) para realizar o check-in.

    Espera um campo 'codigo' que contenha o identificador do QRCode no formato
    gerado em InscricaoEvento. Faz validações mínimas e marca presença.
    Retorna JSON com status.
    """
    if request.method != "POST":  # pragma: no cover - apenas POST suportado
        return HttpResponseBadRequest("Método não suportado.")
    inscricao = get_object_or_404(InscricaoEvento.objects.select_related("evento", "user"), pk=pk)
    evento = inscricao.evento
    user = request.user
    if evento.organizacao != getattr(user, "organizacao", None):
        return HttpResponseForbidden()
    codigo = request.POST.get("codigo", "").strip()
    # Código esperado começa com 'inscricao:' e conter o pk da inscrição
    if not codigo or "inscricao:" not in codigo or f"inscricao:{inscricao.pk}:" not in codigo:
        return HttpResponseBadRequest("Código inválido.")
    if inscricao.status != "confirmada":
        return HttpResponseBadRequest("Inscrição não está confirmada.")
    if inscricao.check_in_realizado_em:
        return JsonResponse({"status": "ok", "message": "Check-in já realizado."})
    inscricao.realizar_check_in()
    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# API Orçamento do Evento (reintroduzido para compatibilidade com testes/rotas)
# ---------------------------------------------------------------------------


@login_required
@no_superadmin_required
def evento_orcamento(request, pk):
    """Atualiza campos de orçamento do evento via POST.

    Espera `orcamento_estimado` e/ou `valor_gasto` (Decimal). Registra log de
    alterações e retorna JSON. Em caso de validação inválida retorna 400 com
    detalhes.
    """
    if request.method != "POST":  # pragma: no cover
        return HttpResponseBadRequest("Método não suportado.")
    evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
    user = request.user
    tipo_usuario = _get_tipo_usuario(user)
    if tipo_usuario not in {UserType.ADMIN.value, UserType.COORDENADOR.value}:
        return HttpResponseForbidden()
    dados = {}
    errors = {}
    for field in ["orcamento_estimado", "valor_gasto"]:
        if field in request.POST and request.POST.get(field) != "":
            raw = request.POST.get(field)
            try:
                dados[field] = Decimal(str(raw))
            except Exception:  # pragma: no cover - conversão genérica
                errors[field] = "valor inválido"
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    alteracoes = {}
    for field, novo_valor in dados.items():
        antigo_valor = getattr(evento, field)
        if antigo_valor != novo_valor:
            alteracoes[field] = {"antes": f"{antigo_valor:.2f}" if antigo_valor is not None else None, "depois": f"{novo_valor:.2f}"}
            setattr(evento, field, novo_valor)
    if alteracoes:
        evento.save(update_fields=list(dados.keys()) + ["updated_at"])
        EventoLog.objects.create(
            evento=evento,
            usuario=user,
            acao="orcamento_atualizado",
            detalhes=alteracoes,
        )
    return JsonResponse({"status": "ok", "alteracoes": alteracoes})


# ---------------------------------------------------------------------------
# API auxiliar: eventos por dia (para calendário / testes)
# ---------------------------------------------------------------------------


@login_required
@no_superadmin_required
def eventos_por_dia(request):
    """Retorna (HTML parcial ou completo) a lista de eventos para um dia ISO.

    Query param: ?dia=YYYY-MM-DD
    Se HTMX (HX-Request), retorna apenas o fragmento de lista.
    Caso contrário, retorna página simples reutilizando template parcial.
    """
    dia_iso = request.GET.get("dia")
    if not dia_iso:
        return HttpResponseBadRequest("Parâmetro 'dia' obrigatório.")
    try:
        dia = date.fromisoformat(dia_iso)
    except ValueError:
        return HttpResponseBadRequest("Data inválida.")
    if getattr(request.user, "user_type", None) == UserType.ROOT:
        return HttpResponseForbidden()
    eventos = (
        _queryset_por_organizacao(request)
        .filter(data_inicio__date=dia)
        .select_related("organizacao", "nucleo")
        .prefetch_related("inscricoes")
        .order_by("data_inicio")
    )
    context = {"dia": dia, "eventos": list(eventos), "title": _("Eventos"), "subtitle": None}
    template = "eventos/partials/calendario/_lista_eventos_dia.html"
    return TemplateResponse(request, template, context)

