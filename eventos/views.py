import calendar
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
from django.db.models import F, Q, Count
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
from django.utils.dateparse import parse_datetime
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

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
    MaterialDivulgacaoEventoForm,
    ParceriaEventoForm,
    TarefaForm,
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
from .tasks import notificar_briefing_status, upload_material_divulgacao

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
        hero_template = self.get_painel_hero_template()
        if hero_template:
            context.setdefault("painel_hero_template", hero_template)
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
        if self.request.headers.get("Hx-Request") == "true":
            return super().render_to_response(context, **response_kwargs)
        context = self.get_painel_context(context)
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

        # anotar número de inscritos por evento
        qs = qs.annotate(num_inscritos=Count("inscricoes", distinct=True))
        return qs.order_by("-data_inicio")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["is_admin_org"] = user.get_tipo_usuario in {UserType.ADMIN.value}
        # Totais baseados no queryset filtrado (sem paginação)
        qs = self.get_queryset()
        ctx["total_eventos"] = qs.count()
        ctx["total_eventos_ativos"] = qs.filter(status=0).count()
        ctx["total_eventos_concluidos"] = qs.filter(status=1).count()
        ctx["total_inscritos"] = InscricaoEvento.objects.filter(evento__in=qs).count()
        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
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
    if request.headers.get("Hx-Request") == "true":
        return TemplateResponse(request, "eventos/partials/calendario/calendario.html", context)
    # Não HTMX: renderiza o painel com o parcial calendário já incluído
    context["partial_template"] = "eventos/partials/calendario/calendario.html"
    context.setdefault("painel_action_template", "eventos/partials/eventos/hero_evento_list_action.html")
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
    painel_title = _("Cadastrar Evento")
    painel_hero_template = "_components/hero.html"

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
    painel_hero_template = "_components/hero.html"

    permission_required = "eventos.change_evento"

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
    painel_hero_template = "_components/hero.html"

    permission_required = "eventos.delete_evento"

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
                "orcamento": evento.orcamento,
                "orcamento_estimado": evento.orcamento_estimado,
                "valor_gasto": evento.valor_gasto,
                "inscricao_confirmada": confirmada,
            }
        )
        context.setdefault("painel_title", evento.titulo)

        return context


class TarefaDetailView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, DetailView):
    model = Tarefa
    template_name = "eventos/partials/tarefas/tarefa_detail.html"
    painel_hero_template = "_components/hero.html"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["logs"] = self.object.logs.select_related("usuario").all()
        context.setdefault("painel_title", self.object.titulo)
        return context


class TarefaListView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, ListView):
    model = Tarefa
    template_name = "eventos/partials/tarefas/tarefa_list.html"
    context_object_name = "tarefas"
    painel_title = _("Tarefas")
    painel_hero_template = "_components/hero.html"

    def get_queryset(self):
        qs = Tarefa.objects.select_related("organizacao", "responsavel")
        user = self.request.user
        if user.user_type == UserType.ROOT:
            return qs
        nucleo_ids = list(user.nucleos.values_list("id", flat=True))
        filtro = Q(organizacao=user.organizacao)
        if nucleo_ids:
            filtro |= Q(nucleo__in=nucleo_ids)
        return qs.filter(filtro)


class TarefaCreateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, CreateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = "eventos/partials/tarefas/tarefa_form.html"
    success_url = reverse_lazy("eventos:tarefa_list")
    painel_title = _("Nova Tarefa")
    painel_hero_template = "_components/hero.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        form.fields["responsavel"].queryset = User.objects.filter(organizacao=user.organizacao)
        return form

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        response = super().form_valid(form)
        TarefaLog.objects.create(tarefa=self.object, usuario=self.request.user, acao="tarefa_criada")
        return response


class TarefaUpdateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, GerenteRequiredMixin, UpdateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = "eventos/partials/tarefas/tarefa_form.html"
    success_url = reverse_lazy("eventos:tarefa_list")
    painel_title = _("Editar Tarefa")
    painel_hero_template = "_components/hero.html"

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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        form.fields["responsavel"].queryset = User.objects.filter(organizacao=user.organizacao)
        return form

    def form_valid(self, form):
        old_instance = Tarefa.objects.get(pk=self.object.pk)
        response = super().form_valid(form)
        changes = {}
        for field in form.changed_data:
            before = getattr(old_instance, field)
            after = getattr(self.object, field)
            if before != after:
                changes[field] = {"antes": before, "depois": after}
        TarefaLog.objects.create(
            tarefa=self.object,
            usuario=self.request.user,
            acao="tarefa_atualizada",
            detalhes=changes,
        )
        return response


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
            inscricao.confirmar_inscricao()
            if inscricao.status == "confirmada":
                messages.success(request, _("Inscrição realizada."))  # pragma: no cover
            else:
                messages.success(request, _("Você está na lista de espera."))  # pragma: no cover
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
        if request.headers.get("Hx-Request") == "true":
            return TemplateResponse(
                request, "eventos/partials/eventos/avaliacao_form.html", context
            )
        context.update(
            {
                "partial_template": "eventos/partials/eventos/avaliacao_form.html",
                "painel_title": _("Avaliar evento"),
                "painel_hero_template": "_components/hero.html",
            }
        )
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
def fila_espera(request, pk: int):
    evento = get_object_or_404(_queryset_por_organizacao(request), pk=pk)
    inscritos = list(
        evento.inscricoes.filter(status="pendente")
        .order_by("posicao_espera")
        .values("user__username", "posicao_espera")
    )
    return JsonResponse({"fila": inscritos})


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

    context = {"parceria": parceria}
    if request.headers.get("Hx-Request") == "true":
        return TemplateResponse(
            request, "eventos/partials/parceria/parceria_avaliar.html", context
        )
    context.update(
        {
            "partial_template": "eventos/partials/parceria/parceria_avaliar.html",
            "painel_title": _("Avaliar parceria"),
            "painel_hero_template": "_components/hero.html",
        }
    )
    return TemplateResponse(request, "eventos/painel.html", context)


@login_required
@no_superadmin_required
def checkin_form(request, pk: int):
    inscricao = get_object_or_404(InscricaoEvento, pk=pk)
    context = {"inscricao": inscricao}
    if request.headers.get("Hx-Request") == "true":
        return TemplateResponse(
            request, "eventos/partials/inscricao/checkin_form.html", context
        )
    context.update(
        {
            "partial_template": "eventos/partials/inscricao/checkin_form.html",
            "painel_title": _("Check-in do evento"),
            "painel_hero_template": "_components/hero.html",
        }
    )
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


class InscricaoEventoCreateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = InscricaoEvento
    form_class = InscricaoEventoForm
    template_name = "eventos/partials/inscricao/inscricao_form.html"
    painel_title = _("Inscrição")
    painel_hero_template = "_components/hero.html"

    def dispatch(self, request, *args, **kwargs):
        self.evento = get_object_or_404(_queryset_por_organizacao(request), pk=kwargs["pk"])
        if request.user.user_type == UserType.ADMIN:
            messages.error(request, _("Administradores não podem se inscrever em eventos."))
            return redirect("eventos:evento_detalhe", pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["evento"] = self.evento
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


class MaterialDivulgacaoEventoListView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ListView):
    model = MaterialDivulgacaoEvento
    template_name = "eventos/partials/eventos/material_list.html"
    context_object_name = "materiais"
    paginate_by = 10
    painel_title = _("Materiais de Divulgação")
    painel_hero_template = "_components/hero.html"

    def get_queryset(self):
        user = self.request.user
        qs = MaterialDivulgacaoEvento.objects.only("id", "titulo", "descricao", "arquivo", "status")
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        try:
            params.pop("page")
        except KeyError:
            pass
        ctx["querystring"] = urlencode(params, doseq=True)
        return ctx


class MaterialDivulgacaoEventoCreateView(
    PainelRenderMixin,
    LoginRequiredMixin,
    NoSuperadminMixin,
    GerenteRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = MaterialDivulgacaoEvento
    form_class = MaterialDivulgacaoEventoForm
    template_name = "eventos/partials/eventos/material_form.html"
    success_url = reverse_lazy("eventos:material_list")
    painel_title = _("Novo Material")
    painel_hero_template = "_components/hero.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if user.user_type != UserType.ROOT:
            form.fields["evento"].queryset = Evento.objects.filter(
                Q(organizacao=user.organizacao) | Q(nucleo__in=user.nucleos.values_list("id", flat=True))
            )
        return form

    permission_required = "eventos.add_materialdivulgacaoevento"

    def form_valid(self, form):
        evento = form.cleaned_data["evento"]
        user = self.request.user
        if user.user_type != UserType.ROOT:
            if evento.organizacao != user.organizacao:
                form.add_error("evento", _("Evento de outra organização"))
                return self.form_invalid(form)
            if not user.nucleos.filter(id=evento.nucleo_id).exists():
                form.add_error("evento", _("Evento de outro núcleo"))
                return self.form_invalid(form)
        response = super().form_valid(form)
        upload_material_divulgacao.delay(self.object.pk)
        EventoLog.objects.create(
            evento=self.object.evento,
            usuario=self.request.user,
            acao="material_criado",
        )
        return response


class MaterialDivulgacaoEventoUpdateView(
    PainelRenderMixin,
    LoginRequiredMixin,
    NoSuperadminMixin,
    GerenteRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = MaterialDivulgacaoEvento
    form_class = MaterialDivulgacaoEventoForm
    template_name = "eventos/partials/eventos/material_form.html"
    success_url = reverse_lazy("eventos:material_list")
    painel_title = _("Editar Material")
    painel_hero_template = "_components/hero.html"

    permission_required = "eventos.change_materialdivulgacaoevento"

    def get_queryset(self):  # pragma: no cover - simples
        qs = MaterialDivulgacaoEvento.objects.all()
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
        arquivo_alterado = False
        for field in form.changed_data:
            before = getattr(old_obj, field)
            after = form.cleaned_data.get(field)
            if before != after:
                detalhes[field] = {"antes": before, "depois": after}
                if field == "arquivo":
                    arquivo_alterado = True
        response = super().form_valid(form)
        if arquivo_alterado:
            upload_material_divulgacao.delay(self.object.pk)
        EventoLog.objects.create(
            evento=self.object.evento,
            usuario=self.request.user,
            acao="material_atualizado",
            detalhes=detalhes,
        )
        return response


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
        nucleo = self.request.GET.get("nucleo")
        if nucleo:
            qs = qs.filter(nucleo_id=nucleo)
        return qs.order_by("-data_inicio")


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


class ParceriaEventoUpdateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ParceriaPermissionMixin, UpdateView):
    model = ParceriaEvento
    form_class = ParceriaEventoForm
    template_name = "eventos/partials/parceria/parceria_form.html"
    success_url = reverse_lazy("eventos:parceria_list")
    painel_title = _("Editar Parceria")
    painel_hero_template = "_components/hero.html"

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


class ParceriaEventoDeleteView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ParceriaPermissionMixin, DeleteView):
    model = ParceriaEvento
    template_name = "eventos/partials/parceria/parceria_confirm_delete.html"
    success_url = reverse_lazy("eventos:parceria_list")
    painel_title = _("Remover Parceria")
    painel_hero_template = "_components/hero.html"

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
            detalhes={},
        )
        return super().delete(request, *args, **kwargs)


class BriefingEventoListView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, ListView):
    model = BriefingEvento
    template_name = "eventos/partials/briefing/briefing_list.html"
    context_object_name = "briefings"
    painel_title = _("Briefings de Eventos")
    painel_hero_template = "_components/hero.html"

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


class BriefingEventoCreateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, CreateView):
    model = BriefingEvento
    form_class = BriefingEventoCreateForm
    template_name = "eventos/partials/briefing/briefing_form.html"
    success_url = reverse_lazy("eventos:briefing_list")
    painel_title = _("Novo Briefing")
    painel_hero_template = "_components/hero.html"

    def form_valid(self, form):
        evento = form.cleaned_data.get("evento")
        if BriefingEvento.objects.filter(evento=evento, deleted=False).exists():
            form.add_error("evento", _("Já existe briefing para este evento."))
            return self.form_invalid(form)
        user = self.request.user
        if user.user_type != UserType.ROOT:
            nucleo_ids = list(user.nucleos.values_list("id", flat=True))
            if not (evento.organizacao == user.organizacao or (evento.nucleo_id and evento.nucleo_id in nucleo_ids)):
                form.add_error("evento", _("Evento de outra organização ou núcleo"))
                return self.form_invalid(form)
        messages.success(self.request, _("Briefing criado com sucesso."))
        return super().form_valid(form)


class BriefingEventoUpdateView(PainelRenderMixin, LoginRequiredMixin, NoSuperadminMixin, UpdateView):
    model = BriefingEvento
    form_class = BriefingEventoForm
    template_name = "eventos/partials/briefing/briefing_form.html"
    success_url = reverse_lazy("eventos:briefing_list")
    painel_title = _("Editar Briefing")
    painel_hero_template = "_components/hero.html"

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
        if not briefing.can_transition_to(status):
            messages.error(request, _("Transição de status inválida."))
            return redirect("eventos:briefing_list")
        now = timezone.now()
        update_fields = ["status", "avaliado_por", "avaliado_em", "updated_at"]
        briefing.avaliado_por = request.user
        briefing.avaliado_em = now
        detalhes = {}
        if status == "orcamentado":
            prazo_str = request.POST.get("prazo_limite_resposta")
            if not prazo_str:
                messages.error(request, _("Informe o prazo limite de resposta."))
                return redirect("eventos:briefing_list")
            prazo = parse_datetime(prazo_str)
            if prazo is None:
                messages.error(request, _("Prazo limite inválido."))
                return redirect("eventos:briefing_list")
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
                return redirect("eventos:briefing_list")
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
        return redirect("eventos:briefing_list")
