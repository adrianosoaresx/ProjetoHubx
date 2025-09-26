import calendar
from collections import Counter
from datetime import date, timedelta, datetime, time
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django import forms
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError
from django.db.models import F, Q, Count, Model
from django.db.models.fields.files import FieldFile
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.functional import Promise
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import UserType
from core.permissions import (
    AdminRequiredMixin,
    GerenteRequiredMixin,
    NoSuperadminMixin,
    no_superadmin_required,
)

from .forms import (
    BriefingEventoCreateForm,
    BriefingEventoForm,
    EventoForm,
    InscricaoEventoForm,
    ParceriaEventoForm,
)
from .models import (
    BriefingEvento,
    Evento,
    EventoLog,
    FeedbackNota,
    InscricaoEvento,
    ParceriaEvento,
)
from .tasks import notificar_briefing_status

User = get_user_model()


class PainelRenderMixin:
    painel_template_name = "eventos/painel.html"
    painel_title = _("Eventos")
    painel_hero_template = "_components/hero_evento.html"
    painel_action_template = None
    painel_subtitle = None
    painel_breadcrumb_template = None
    painel_neural_background = None
    painel_hero_style = None

    def get_partial_template_name(self) -> str:
        return self.template_name

    def get_painel_title(self) -> str:
        return getattr(self, "painel_title", _("Eventos"))

    def get_painel_hero_template(self) -> str | None:
        return getattr(self, "painel_hero_template", "_components/hero_evento.html")

    def get_painel_action_template(self) -> str | None:
        return getattr(self, "painel_action_template", None)

    def get_painel_subtitle(self) -> str | None:
        return getattr(self, "painel_subtitle", None)

    def get_painel_breadcrumb_template(self) -> str | None:
        return getattr(self, "painel_breadcrumb_template", None)

    def get_painel_neural_background(self) -> str | None:
        return getattr(self, "painel_neural_background", None)

    def get_painel_hero_style(self) -> str | None:
        return getattr(self, "painel_hero_style", None)

    def get_painel_context(self, context: dict) -> dict:
        context.setdefault("painel_title", self.get_painel_title())
        # Variáveis padrão para navegação e heros que podem ser opcionais
        context.setdefault("briefing_url", None)
        context.setdefault("briefing_evento", None)
        context.setdefault("briefing_label", None)
        context.setdefault("evento", None)
        hero_template = self.get_painel_hero_template()
        if hero_template:
            context.setdefault("painel_hero_template", hero_template)
        # Se houver um evento no contexto, forçar o hero de detalhes do evento
        if context.get("evento") is not None:
            context["painel_hero_template"] = "_components/hero_eventos_detail.html"
            # Se não houver título definido, usar o título do evento
            if not context.get("painel_title") and getattr(context["evento"], "titulo", None):
                context["painel_title"] = context["evento"].titulo
        action_template = self.get_painel_action_template()
        if action_template:
            context.setdefault("painel_action_template", action_template)
        subtitle = self.get_painel_subtitle()
        if subtitle:
            context.setdefault("painel_subtitle", subtitle)
        breadcrumb = self.get_painel_breadcrumb_template()
        if breadcrumb:
            context.setdefault("painel_breadcrumb_template", breadcrumb)
        neural_background = self.get_painel_neural_background()
        if neural_background:
            context.setdefault("painel_neural_background", neural_background)
        hero_style = self.get_painel_hero_style()
        if hero_style:
            context.setdefault("painel_hero_style", hero_style)
        return context

    def render_to_response(self, context, **response_kwargs):
        is_htmx_request = self.request.headers.get("HX-Request") == "true"
        context = self.get_painel_context(context)
        context["is_htmx"] = is_htmx_request
        # Responder apenas com o parcial quando for requisição HTMX
        if is_htmx_request:
            return super().render_to_response(context, **response_kwargs)
        context["partial_template"] = self.get_partial_template_name()
        return TemplateResponse(self.request, self.painel_template_name, context)


class EventoListView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ListView):
    template_name = "eventos/partials/eventos/evento_list.html"
    painel_action_template = "eventos/partials/eventos/hero_evento_list_action.html"
    context_object_name = "eventos"
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Count

        qs = (
            Evento.objects.filter(organizacao=user.organizacao)
            .select_related("nucleo", "coordenador", "organizacao")
            .prefetch_related("inscricoes")
        )

        # Visibilidade:
        # - ADMIN: vê todos os eventos da organização
        # - COORDENADOR/NUCLEADO (não ROOT): vê eventos públicos da organização ou do(s) seu(s) núcleo(s)
        if user.get_tipo_usuario not in {UserType.ADMIN.value, UserType.ROOT.value}:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            qs = qs.filter(Q(publico_alvo=0) | Q(nucleo__in=nucleo_ids)).distinct()

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(descricao__icontains=q) | Q(nucleo__nome__icontains=q))

        status_filter = self.request.GET.get("status")
        status_map = {"ativos": 0, "realizados": 1}
        if status_filter in status_map:
            qs = qs.filter(status=status_map[status_filter])

        # anotar número de inscritos por evento
        qs = qs.annotate(num_inscritos=Count("inscricoes", distinct=True))
        return qs.order_by("-data_inicio")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["is_admin_org"] = user.get_tipo_usuario in {UserType.ADMIN.value}
        current_filter = self.request.GET.get("status") or ""
        if current_filter not in {"ativos", "realizados"}:
            current_filter = "todos"
        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass

        def build_url(filter_value: str | None) -> str:
            query_params = params.copy()
            if filter_value in {"ativos", "realizados"}:
                query_params["status"] = filter_value
            else:
                query_params.pop("status", None)
            query_string = query_params.urlencode()
            return f"{self.request.path}?{query_string}" if query_string else self.request.path

        ctx["current_filter"] = current_filter
        ctx["ativos_filter_url"] = build_url("ativos")
        ctx["realizados_filter_url"] = build_url("realizados")
        ctx["todos_filter_url"] = build_url(None)
        ctx["is_ativos_filter_active"] = current_filter == "ativos"
        ctx["is_realizados_filter_active"] = current_filter == "realizados"

        # Totais baseados no queryset filtrado (sem paginação)
        qs = self.get_queryset()
        ctx["total_eventos"] = qs.count()
        ctx["total_eventos_ativos"] = qs.filter(status=0).count()
        ctx["total_eventos_concluidos"] = qs.filter(status=1).count()
        ctx["total_inscritos"] = InscricaoEvento.objects.filter(evento__in=qs).count()
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["querystring"] = urlencode(params, doseq=True)
        return ctx

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
    return redirect("eventos:painel")


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
        {"data": d, "eventos": evs}
        for d, evs in sorted(agrupado.items(), key=lambda x: x[0], reverse=True)
    ]

    context = {
        "dias_com_eventos": dias_com_eventos,
        "data_atual": hoje,
    }
    hero_context = {
        "painel_title": _("Eventos"),
        "painel_hero_template": "_components/hero_evento.html",
    }
    is_htmx = request.headers.get("HX-Request") == "true"
    context.update(hero_context)
    context["is_htmx"] = is_htmx
    if is_htmx:
        return TemplateResponse(request, "eventos/partials/calendario/calendario.html", context)
    # Não HTMX: renderiza o painel com o parcial calendário já incluído
    context["partial_template"] = "eventos/partials/calendario/calendario.html"
    context.setdefault("painel_action_template", "eventos/partials/eventos/hero_evento_list_action.html")
    # Garantir que o hero tenha um título explícito ao renderizar o painel
    context.setdefault("painel_title", _("Eventos"))
    return TemplateResponse(request, "eventos/painel.html", context)


def lista_eventos(request, dia_iso):
    return HttpResponseBadRequest("Endpoint não suportado.")
def painel_eventos(request):
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
        {"data": d, "eventos": evs}
        for d, evs in sorted(agrupado.items(), key=lambda x: x[0], reverse=True)
    ]

    context = {
        "dias_com_eventos": dias_com_eventos,
        "data_atual": hoje,
        "partial_template": "eventos/partials/calendario/calendario.html",
        "painel_action_template": "eventos/partials/eventos/hero_evento_list_action.html",
        # Garantir título do hero neste painel funcional
        "painel_title": _("Eventos"),
    }
    return TemplateResponse(request, "eventos/painel.html", context)


class EventoCreateView(
    PainelRenderMixin,
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/partials/eventos/create.html"
    success_url = reverse_lazy("eventos:calendario")
    painel_title = _("Adicionar evento")
    painel_subtitle = _("Cadastre novos eventos para a sua organização.")
    painel_hero_template = "_components/hero_evento.html"

    permission_required = "eventos.add_evento"

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type == UserType.ROOT:
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
    PainelRenderMixin,
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/partials/eventos/update.html"
    success_url = reverse_lazy("eventos:calendario")
    painel_title = _("Editar Evento")
    painel_hero_template = "_components/hero_eventos_detail.html"

    permission_required = "eventos.change_evento"

    def get_queryset(self):  # pragma: no cover
        return _queryset_por_organizacao(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.object
        return context

    def form_valid(self, form):  # pragma: no cover
        """Registra log comparando campos alterados."""

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
                detalhes[field] = {
                    "antes": _serialize_value(before),
                    "depois": _serialize_value(after),
                }

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
    PainelRenderMixin,
    LoginRequiredMixin,
    NoSuperadminMixin,
    AdminRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    model = Evento
    template_name = "eventos/partials/eventos/delete.html"
    success_url = reverse_lazy("eventos:calendario")
    painel_title = _("Remover Evento")
    painel_hero_template = "_components/hero_eventos_detail.html"

    permission_required = "eventos.delete_evento"

    def get_queryset(self):  # pragma: no cover
        return _queryset_por_organizacao(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # disponibiliza o objeto como `evento` para o hero de detalhes
        context["evento"] = self.object
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
        return super().delete(request, *args, **kwargs)  # pragma: no cover


class EventoDetailView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, DetailView):
    model = Evento
    template_name = "eventos/partials/eventos/detail.html"
    painel_hero_template = "_components/hero_eventos_detail.html"

    def get_queryset(self):
        user = self.request.user
        base = Evento.objects.select_related("organizacao").prefetch_related("inscricoes", "feedbacks")
        # ROOT já é bloqueado por NoSuperadminMixin
        if user.user_type == UserType.ADMIN:
            return base.filter(organizacao=user.organizacao)
        # Associados / Coordenadores / Nucleados: leitura de eventos públicos da org ou do(s) seu(s) núcleo(s)
        nucleo_ids = list(user.nucleos.values_list("id", flat=True))
        return base.filter(organizacao=user.organizacao).filter(Q(publico_alvo=0) | Q(nucleo__in=nucleo_ids)).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        evento: Evento = self.object
        context["evento"] = evento
        minha_inscricao = evento.inscricoes.filter(user=user, status="confirmada").select_related("user").first()
        confirmada = bool(minha_inscricao)
        context["inscricao_confirmada"] = confirmada
        context["avaliacao_permitida"] = confirmada and timezone.now() > evento.data_fim
        context["inscricao"] = minha_inscricao

        evento = context["object"]
        inscricoes = list(evento.inscricoes.all())
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
            media_feedback = sum(feedback.nota for feedback in feedbacks) / total_feedbacks
        context.update(
            {
                "local": evento.local,
                "cidade": evento.cidade,
                "estado": evento.estado,
                "cep": evento.cep,
                "contato_nome": evento.contato_nome,
                "contato_email": evento.contato_email,
                "contato_whatsapp": evento.contato_whatsapp,
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
            }
        )
        context["painel_title"] = evento.titulo
        context["painel_hero_template"] = self.get_painel_hero_template()

        briefing_evento = BriefingEvento.objects.filter(evento=evento).first()
        if briefing_evento:
            context["briefing_evento"] = briefing_evento
            context["briefing_url"] = reverse(
                "eventos:briefing_detalhe", kwargs={"evento_pk": evento.pk}
            )
            context.setdefault("briefing_label", _("Briefing do evento"))

        return context


class EventoSubscribeView(LoginRequiredMixin, NoSuperadminMixin, View):
    """Inscreve ou cancela a inscrição do usuário no evento."""

    def post(self, request, pk):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        if request.user.user_type == UserType.ADMIN:
            messages.error(request, _("Administradores não podem se inscrever em eventos."))  # pragma: no cover
            return redirect("eventos:evento_detalhe", pk=pk)

        inscricao, created = InscricaoEvento.objects.get_or_create(user=request.user, evento=evento)
        if inscricao.status == "confirmada":
            try:
                inscricao.cancelar_inscricao()
                messages.success(request, _("Inscrição cancelada."))  # pragma: no cover
            except ValueError as exc:
                messages.error(request, str(exc))
        else:
            try:
                inscricao.confirmar_inscricao()
            except ValueError as exc:
                if created:
                    inscricao.delete()
                messages.error(request, str(exc))
            else:
                messages.success(request, _("Inscrição realizada."))  # pragma: no cover
        return redirect("eventos:evento_detalhe", pk=pk)


class EventoRemoveInscritoView(LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, View):
    """Remove um inscrito do evento."""

    def post(self, request, pk, user_id):  # pragma: no cover
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        if (
            request.user.user_type in {UserType.ADMIN, UserType.COORDENADOR}
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
        return redirect("eventos:evento_editar", pk=pk)


class EventoFeedbackView(LoginRequiredMixin, NoSuperadminMixin, View):
    """Registra feedback pós-evento."""

    def get(self, request, pk):
        evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
        usuario = request.user

        if not InscricaoEvento.objects.filter(user=usuario, evento=evento, status="confirmada").exists():
            return HttpResponseForbidden("Apenas inscritos podem enviar feedback.")

        if timezone.now() < evento.data_fim:
            return HttpResponseForbidden("Feedback só pode ser enviado após o evento.")

        context = {"evento": evento}
        hero_context = {
            "painel_title": _("Avaliar evento"),
            "painel_hero_template": "_components/hero_eventos_detail.html",
        }
        is_htmx = request.headers.get("HX-Request") == "true"
        context.update(hero_context)
        context["is_htmx"] = is_htmx
        if is_htmx:
            return TemplateResponse(
                request, "eventos/partials/eventos/avaliacao_form.html", context
            )
        context["partial_template"] = "eventos/partials/eventos/avaliacao_form.html"
        return TemplateResponse(request, "eventos/painel.html", context)

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


def eventos_por_dia(request):
    """Compatível com reverse('eventos:eventos_por_dia') via ?dia=YYYY-MM-DD"""
    dia_iso = request.GET.get("dia")
    if not dia_iso:
        raise Http404("Parâmetro 'dia' ausente.")
    if getattr(request.user, "user_type", None) == UserType.ROOT:
        return HttpResponseForbidden()
    return lista_eventos(request, dia_iso)


@login_required
@no_superadmin_required
def evento_orcamento(request, pk: int):
    evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
    if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR}:
        return HttpResponseForbidden()
    if request.method == "POST":

        class _Form(forms.Form):
            orcamento_estimado = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
            valor_gasto = forms.DecimalField(max_digits=10, decimal_places=2, required=False)

        form = _Form(request.POST)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)

        orcamento_estimado = form.cleaned_data.get("orcamento_estimado") or Decimal("0")
        valor_gasto = form.cleaned_data.get("valor_gasto") or Decimal("0")

        old_orcamento = evento.orcamento_estimado
        old_valor = evento.valor_gasto

        evento.orcamento_estimado = orcamento_estimado
        evento.valor_gasto = valor_gasto
        evento.save(update_fields=["orcamento_estimado", "valor_gasto", "updated_at"])

        detalhes: dict[str, dict[str, Decimal]] = {}
        if old_orcamento != orcamento_estimado:
            detalhes["orcamento_estimado"] = {"antes": old_orcamento, "depois": orcamento_estimado}
        if old_valor != valor_gasto:
            detalhes["valor_gasto"] = {"antes": old_valor, "depois": valor_gasto}
        if detalhes:
            EventoLog.objects.create(
                evento=evento,
                usuario=request.user,
                acao="orcamento_atualizado",
                detalhes=detalhes,
            )

    data = {"orcamento_estimado": evento.orcamento_estimado, "valor_gasto": evento.valor_gasto}
    return JsonResponse(data)
@login_required
@no_superadmin_required
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

    if request.method == "POST":
        if parceria.avaliacao is not None:
            return JsonResponse({"error": _("Parceria já avaliada.")}, status=400)
        try:
            parceria.avaliacao = int(request.POST.get("nota"))
            if not 1 <= parceria.avaliacao <= 5:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse({"error": _("Nota inválida.")}, status=400)
        parceria.comentario = request.POST.get("comentario", "")
        parceria.save(update_fields=["avaliacao", "comentario", "updated_at"])
        return JsonResponse(
            {
                "success": _("Avaliação registrada com sucesso."),
                "avaliacao": parceria.avaliacao,
                "comentario": parceria.comentario,
            }
        )

    context = {"parceria": parceria, "evento": parceria.evento}
    hero_context = {
        "painel_title": _("Avaliar parceria"),
        "painel_hero_template": "_components/hero_eventos_detail.html",
    }
    is_htmx = request.headers.get("HX-Request") == "true"
    context.update(hero_context)
    context["is_htmx"] = is_htmx
    if is_htmx:
        return TemplateResponse(
            request, "eventos/partials/parceria/parceria_avaliar.html", context
        )
    context["partial_template"] = "eventos/partials/parceria/parceria_avaliar.html"
    return TemplateResponse(request, "eventos/painel.html", context)


@login_required
@no_superadmin_required
def checkin_form(request, pk: int):
    inscricao = get_object_or_404(InscricaoEvento, pk=pk)
    context = {"inscricao": inscricao, "evento": inscricao.evento}
    hero_context = {
        "painel_title": _("Check-in do evento"),
        "painel_hero_template": "_components/hero_eventos_detail.html",
    }
    is_htmx = request.headers.get("HX-Request") == "true"
    context.update(hero_context)
    context["is_htmx"] = is_htmx
    if is_htmx:
        return TemplateResponse(
            request, "eventos/partials/inscricao/checkin_form.html", context
        )
    context["partial_template"] = "eventos/partials/inscricao/checkin_form.html"
    return TemplateResponse(request, "eventos/painel.html", context)


def checkin_inscricao(request, pk: int):
    """Valida o QRCode enviado e registra o check-in."""
    if getattr(request.user, "user_type", None) == UserType.ROOT:
        return HttpResponseForbidden()
    if request.method != "POST":
        return HttpResponse(status=405)
    inscricao = get_object_or_404(InscricaoEvento, pk=pk)
    codigo = request.POST.get("codigo")
    expected = f"inscricao:{inscricao.pk}:{int(inscricao.created_at.timestamp())}"
    if codigo != expected or inscricao.check_in_realizado_em:
        return HttpResponseForbidden("QR inválido ou já usado")
    inscricao.realizar_check_in()
    return JsonResponse({"check_in": inscricao.check_in_realizado_em})


class InscricaoEventoListView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, ListView):
    model = InscricaoEvento
    template_name = "eventos/partials/inscricao/inscricao_list.html"
    context_object_name = "inscricoes"
    painel_title = _("Lista de Inscrições")
    painel_hero_template = "_components/hero.html"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ev_id = self.request.GET.get("evento")
        if ev_id:
            try:
                # Restringe por organização
                context["evento"] = _queryset_por_organizacao(self.request).get(pk=ev_id)
                context["painel_hero_template"] = "_components/hero_eventos_detail.html"
                context["painel_title"] = context["evento"].titulo
            except Evento.DoesNotExist:
                context["evento"] = None
        return context


class InscricaoEventoCreateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = InscricaoEvento
    form_class = InscricaoEventoForm
    template_name = "eventos/partials/inscricao/inscricao_form.html"
    painel_title = _("Inscrição")
    painel_hero_template = "_components/hero_eventos_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.evento = get_object_or_404(_queryset_por_organizacao(request), pk=kwargs["pk"])
        if request.user.user_type == UserType.ADMIN:
            messages.error(request, _("Administradores não podem se inscrever em eventos."))
            return redirect("eventos:evento_detalhe", pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.evento
        context["painel_title"] = self.evento.titulo
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


class ParceriaPermissionMixin(UserPassesTestMixin):
    def test_func(self) -> bool:  # pragma: no cover - simples
        return self.request.user.user_type in {
            UserType.ADMIN,
            UserType.COORDENADOR,
            UserType.ROOT,
        }


class ParceriaEventoListView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ParceriaPermissionMixin, ListView):
    model = ParceriaEvento
    template_name = "eventos/partials/parceria/parceria_list.html"
    context_object_name = "parcerias"
    painel_title = _("Parcerias")
    painel_hero_template = "_components/hero.html"

    def get_queryset(self):
        user = self.request.user
        qs = ParceriaEvento.objects.select_related("evento", "nucleo")
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        evento_param = self.request.GET.get("evento")
        if evento_param:
            qs = qs.filter(evento_id=evento_param)
        nucleo = self.request.GET.get("nucleo")
        if nucleo:
            qs = qs.filter(nucleo_id=nucleo)
        return qs.order_by("-data_inicio")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ev_id = self.request.GET.get("evento")
        if ev_id:
            try:
                context["evento"] = _queryset_por_organizacao(self.request).get(pk=ev_id)
                context["painel_hero_template"] = "_components/hero_eventos_detail.html"
                context["painel_title"] = context["evento"].titulo
                # também disponibiliza link do briefing se existir
                briefing_evento = BriefingEvento.objects.filter(evento_id=ev_id).first()
                if briefing_evento:
                    context["briefing_evento"] = briefing_evento
                    context["briefing_url"] = reverse("eventos:briefing_detalhe", kwargs={"evento_pk": ev_id})
                    context.setdefault("briefing_label", _("Briefing do evento"))
            except Evento.DoesNotExist:
                context["evento"] = None
        return context


class ParceriaEventoCreateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ParceriaPermissionMixin, CreateView):
    model = ParceriaEvento
    form_class = ParceriaEventoForm
    template_name = "eventos/partials/parceria/parceria_form.html"
    success_url = reverse_lazy("eventos:parceria_list")
    painel_title = _("Nova Parceria")
    painel_hero_template = "_components/hero.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if user.user_type != UserType.ROOT:
            form.fields["evento"].queryset = Evento.objects.filter(
                Q(organizacao=user.organizacao) | Q(nucleo__in=user.nucleos.values_list("id", flat=True))
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ev_id = self.request.GET.get("evento")
        if ev_id:
            try:
                context["evento"] = _queryset_por_organizacao(self.request).get(pk=ev_id)
                context["painel_hero_template"] = "_components/hero_eventos_detail.html"
                context.setdefault("painel_title", context["evento"].titulo)
            except Evento.DoesNotExist:
                pass
        return context


class ParceriaEventoUpdateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ParceriaPermissionMixin, UpdateView):
    model = ParceriaEvento
    form_class = ParceriaEventoForm
    template_name = "eventos/partials/parceria/parceria_form.html"
    success_url = reverse_lazy("eventos:parceria_list")
    painel_title = _("Editar Parceria")
    painel_hero_template = "_components/hero_eventos_detail.html"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.object.evento
        return context


class ParceriaEventoDeleteView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ParceriaPermissionMixin, DeleteView):
    model = ParceriaEvento
    template_name = "eventos/partials/parceria/parceria_confirm_delete.html"
    success_url = reverse_lazy("eventos:parceria_list")
    painel_title = _("Remover Parceria")
    painel_hero_template = "_components/hero_eventos_detail.html"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.object.evento
        return context

    def delete(self, request, *args, **kwargs):  # pragma: no cover
        self.object = self.get_object()
        EventoLog.objects.create(
            evento=self.object.evento,
            usuario=request.user,
            acao="parceria_excluida",
            detalhes={},
        )
        return super().delete(request, *args, **kwargs)


class BriefingEventoCreateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = BriefingEvento
    form_class = BriefingEventoCreateForm
    template_name = "eventos/partials/briefing/briefing_form.html"
    painel_title = _("Novo Briefing")
    painel_hero_template = "_components/hero.html"

    def form_valid(self, form):
        evento = form.cleaned_data.get("evento")
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            if not (evento.organizacao == user.organizacao or (evento.nucleo_id and evento.nucleo_id in nucleo_ids)):
                form.add_error("evento", _("Evento de outra organização ou núcleo"))
                return self.form_invalid(form)
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("evento", _("Já existe briefing para este evento."))
            return self.form_invalid(form)
        messages.success(self.request, _("Briefing criado com sucesso."))
        return response

    def get_success_url(self):
        return reverse("eventos:briefing_detalhe", kwargs={"evento_pk": self.object.evento_id})


class BriefingEventoDetailView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, UpdateView):
    model = BriefingEvento
    form_class = BriefingEventoForm
    template_name = "eventos/partials/briefing/briefing_detail.html"
    context_object_name = "briefing"
    painel_title = _("Briefing do Evento")
    painel_hero_template = "_components/hero_eventos_detail.html"
    pk_url_kwarg = "evento_pk"

    def get_queryset(self):
        qs = BriefingEvento.objects.select_related("evento")
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            filtro = Q(evento__organizacao=user.organizacao)
            if nucleo_ids:
                filtro |= Q(evento__nucleo__in=nucleo_ids)
            qs = qs.filter(filtro)
        return qs

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        evento_pk = self.kwargs.get(self.pk_url_kwarg)
        if not evento_pk:
            raise Http404
        return get_object_or_404(queryset, evento_id=evento_pk)

    def get_success_url(self):
        return reverse("eventos:briefing_detalhe", kwargs={"evento_pk": self.object.evento_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        briefing = context.get("briefing") or self.object
        context["evento"] = briefing.evento
        context["briefing_evento"] = briefing.evento
        context["briefing_url"] = reverse(
            "eventos:briefing_detalhe",
            kwargs={"evento_pk": briefing.evento.pk},
        )
        context["available_transitions"] = briefing.STATUS_TRANSITIONS.get(briefing.status, set())
        context["painel_title"] = _("Briefing de %(evento)s") % {"evento": briefing.evento.titulo}
        return context

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
        messages.success(self.request, _("Briefing atualizado com sucesso."))
        return response


class BriefingEventoStatusView(LoginRequiredMixin, NoSuperadminMixin, View):
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
        detail_url = reverse("eventos:briefing_detalhe", kwargs={"evento_pk": briefing.evento_id})
        if not briefing.can_transition_to(status):
            messages.error(request, _("Transição de status inválida."))
            return redirect(detail_url)
        now = timezone.now()
        update_fields = ["status", "avaliado_por", "avaliado_em", "updated_at"]
        briefing.avaliado_por = request.user
        briefing.avaliado_em = now
        detalhes = {}
        if status == "orcamentado":
            prazo_str = request.POST.get("prazo_limite_resposta")
            if not prazo_str:
                messages.error(request, _("Informe o prazo limite de resposta."))
                return redirect(detail_url)
            prazo = parse_datetime(prazo_str)
            if prazo is None:
                messages.error(request, _("Prazo limite inválido."))
                return redirect(detail_url)
            if timezone.is_naive(prazo):
                prazo = timezone.make_aware(prazo)
            briefing.status = "orcamentado"
            briefing.orcamento_enviado_em = now
            briefing.prazo_limite_resposta = prazo
            update_fields.extend(["orcamento_enviado_em", "prazo_limite_resposta"])
        elif status == "aprovado":
            briefing.status = "aprovado"
            briefing.aprovado_em = now
            briefing.coordenadora_aprovou = True
            update_fields.extend(["aprovado_em", "coordenadora_aprovou"])
        elif status == "recusado":
            motivo = request.POST.get("motivo_recusa", "").strip()
            if not motivo:
                messages.error(request, _("Informe o motivo da recusa."))
                return redirect(detail_url)
            briefing.status = "recusado"
            briefing.recusado_em = now
            briefing.recusado_por = request.user
            briefing.motivo_recusa = motivo
            update_fields.extend(["recusado_em", "motivo_recusa", "recusado_por"])
            detalhes["motivo_recusa"] = motivo
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
        return redirect(detail_url)
