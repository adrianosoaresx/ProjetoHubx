from __future__ import annotations

import logging

import tablib
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from accounts.models import UserType
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin

from .forms import (
    MembroRoleForm,
    NucleoForm,
    NucleoSearchForm,
    ParticipacaoDecisaoForm,
    SuplenteForm,
)
from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from .services import gerar_convite_nucleo
from .tasks import (
    notify_exportacao_membros,
    notify_participacao_aprovada,
    notify_participacao_recusada,
    notify_suplente_designado,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class NucleoListView(LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/list.html"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        q = self.request.GET.get("q", "")
        cache_key = f"nucleos_list:{user.id}:{q}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        qs = (
            Nucleo.objects.select_related("organizacao")
            .prefetch_related("participacoes")
            .filter(deleted=False)
            .annotate(
                membros_count=Count(
                    "participacoes",
                    filter=Q(
                        participacoes__status="ativo",
                        participacoes__status_suspensao=False,
                    ),
                    distinct=True,
                )
            )
        )

        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(slug__icontains=q))

        result = list(qs.order_by("nome").distinct())
        cache.set(cache_key, result, 300)
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        return ctx


class NucleoMeusView(LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/meus_list.html"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        q = self.request.GET.get("q", "")
        cache_key = f"nucleos_meus:{user.id}:{q}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        qs = (
            Nucleo.objects.select_related("organizacao")
            .prefetch_related("participacoes")
            .filter(
                deleted=False,
                participacoes__user=user,
                participacoes__status="ativo",
                participacoes__status_suspensao=False,
            )
            .annotate(
                membros_count=Count(
                    "participacoes",
                    filter=Q(
                        participacoes__status="ativo",
                        participacoes__status_suspensao=False,
                    ),
                    distinct=True,
                )
            )
        )

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(slug__icontains=q))

        result = list(qs.order_by("nome").distinct())
        cache.set(cache_key, result, 300)
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        return ctx


class NucleoCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/create.html"
    success_url = reverse_lazy("nucleos:list")

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, _("Núcleo criado com sucesso."))
        return super().form_valid(form)


class NucleoUpdateView(GerenteRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/update.html"
    success_url = reverse_lazy("nucleos:list")

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    def form_valid(self, form):
        messages.success(self.request, _("Núcleo atualizado com sucesso."))
        return super().form_valid(form)


class NucleoDeleteView(AdminRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        return render(request, "nucleos/delete.html", {"object": nucleo})

    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        nucleo.soft_delete()
        messages.success(request, _("Núcleo removido."))
        return redirect("nucleos:list")


class NucleoDetailView(GerenteRequiredMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/detail.html"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nucleo = self.object
        ctx["membros_ativos"] = nucleo.participacoes.filter(status="ativo")
        ctx["coordenadores"] = nucleo.participacoes.filter(status="ativo", papel="coordenador")
        if self.request.user.user_type in {UserType.ADMIN, UserType.COORDENADOR}:
            ctx["membros_pendentes"] = nucleo.participacoes.filter(status="pendente")
            ctx["suplentes"] = nucleo.coordenadores_suplentes.all()
            ctx["convites_pendentes"] = nucleo.convitenucleo_set.filter(usado_em__isnull=True).count()
            limite = getattr(settings, "CONVITE_NUCLEO_DIARIO_LIMITE", 5)
            cache_key = f"convites_nucleo:{self.request.user.id}:{timezone.now().date()}"
            count = cache.get(cache_key, 0)
            ctx["convites_restantes"] = max(limite - count, 0)
        part = nucleo.participacoes.filter(user=self.request.user).first()
        ctx["mostrar_solicitar"] = not part or part.status == "inativo"
        ctx["pode_postar"] = bool(part and part.status == "ativo" and not part.status_suspensao)
        return ctx


class NucleoMetricsView(GerenteRequiredMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/metrics.html"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False)
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        nucleo = self.object
        ctx["nucleo"] = nucleo
        ctx["metrics_url"] = reverse("nucleos_api:nucleo-metrics", args=[nucleo.pk])
        relatorio_base = reverse("nucleos_api:nucleo-relatorio")
        ctx["relatorio_csv_url"] = f"{relatorio_base}?formato=csv"
        ctx["relatorio_pdf_url"] = f"{relatorio_base}?formato=pdf"
        return ctx


class SolicitarParticipacaoModalView(LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        return render(request, "nucleos/solicitar_modal.html", {"nucleo": nucleo})


class PostarFeedModalView(LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        return render(request, "nucleos/postar_modal.html", {"nucleo": nucleo})


class ConvitesModalView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        convites = nucleo.convitenucleo_set.filter(usado_em__isnull=True)
        limite = getattr(settings, "CONVITE_NUCLEO_DIARIO_LIMITE", 5)
        cache_key = f"convites_nucleo:{request.user.id}:{timezone.now().date()}"
        count = cache.get(cache_key, 0)
        restantes = max(limite - count, 0)
        return render(
            request,
            "nucleos/convites_modal.html",
            {
                "nucleo": nucleo,
                "convites": convites,
                "convites_restantes": restantes,
                "create_url": reverse("nucleos:convite_create", args=[nucleo.pk]),
            },
        )


class ConviteCreateView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        email = request.POST.get("email", "")
        papel = request.POST.get("papel", "membro")
        try:
            convite = gerar_convite_nucleo(request.user, nucleo, email, papel)
        except ValueError as exc:
            return HttpResponse(str(exc), status=429)
        csrf_token = get_token(request)
        delete_url = reverse(
            "nucleos_api:nucleo-revogar-convite", args=[nucleo.pk, convite.pk]
        )
        li_html = format_html(
            '<li id="convite-{}" class="flex justify-between items-center">'
            '<span>{} - {}</span>'
            '<form hx-delete="{}" hx-target="#convite-{}" hx-swap="outerHTML" '
            'hx-confirm="{}">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<button type="submit" class="text-red-600">{}</button>'
            '</form></li>',
            convite.id,
            convite.email,
            convite.papel,
            delete_url,
            convite.id,
            _("Confirmar revogação?"),
            csrf_token,
            _("Revogar"),
        )
        return HttpResponse(li_html, status=201)


class ParticipacaoCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        ParticipacaoNucleo.objects.get_or_create(user=request.user, nucleo=nucleo)
        messages.success(request, _("Solicitação enviada."))
        return redirect("nucleos:detail", pk=pk)


class ParticipacaoDecisaoView(GerenteRequiredMixin, LoginRequiredMixin, FormView):
    form_class = ParticipacaoDecisaoForm

    def form_valid(self, form):
        nucleo = get_object_or_404(Nucleo, pk=self.kwargs["pk"])
        participacao = get_object_or_404(ParticipacaoNucleo, pk=self.kwargs["participacao_id"], nucleo=nucleo)
        if participacao.status != "pendente":
            return redirect("nucleos:detail", pk=nucleo.pk)
        participacao.decidido_por = self.request.user
        participacao.data_decisao = timezone.now()
        if form.cleaned_data["acao"] == "approve":
            participacao.status = "ativo"
            participacao.save(update_fields=["status", "decidido_por", "data_decisao"])
            notify_participacao_aprovada.delay(participacao.id)
        else:
            participacao.status = "inativo"
            participacao.save(update_fields=["status", "decidido_por", "data_decisao"])
            notify_participacao_recusada.delay(participacao.id)
        return redirect("nucleos:detail", pk=nucleo.pk)


class MembroRemoveView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        participacao.delete()
        messages.success(request, _("Membro removido do núcleo."))
        return redirect("nucleos:detail", pk=pk)


class MembroRoleView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        form = MembroRoleForm(request.POST, instance=participacao)
        if form.is_valid():
            form.save()
        return redirect("nucleos:detail", pk=pk)


class SuplenteCreateView(GerenteRequiredMixin, LoginRequiredMixin, CreateView):
    model = CoordenadorSuplente
    form_class = SuplenteForm
    template_name = "nucleos/suplente_form.html"

    def get_nucleo(self) -> Nucleo:
        return get_object_or_404(Nucleo, pk=self.kwargs["pk"], deleted=False)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["nucleo"] = self.get_nucleo()
        return kwargs

    def form_valid(self, form):
        nucleo = self.get_nucleo()
        form.instance.nucleo = nucleo
        user = form.cleaned_data["usuario"]
        inicio = form.cleaned_data["periodo_inicio"]
        fim = form.cleaned_data["periodo_fim"]
        if not ParticipacaoNucleo.objects.filter(nucleo=nucleo, user=user, status="ativo").exists():
            form.add_error("usuario", _("Usuário não é membro do núcleo."))
            return self.form_invalid(form)
        overlap = CoordenadorSuplente.objects.filter(
            nucleo=nucleo,
            usuario=user,
            deleted=False,
            periodo_inicio__lt=fim,
            periodo_fim__gt=inicio,
        ).exists()
        if overlap:
            form.add_error(None, _("Usuário já é suplente no período informado."))
            return self.form_invalid(form)
        response = super().form_valid(form)
        notify_suplente_designado.delay(nucleo.id, form.instance.usuario.email)
        messages.success(self.request, _("Suplente adicionado."))
        return response

    def get_success_url(self):
        return reverse_lazy("nucleos:detail", kwargs={"pk": self.kwargs["pk"]})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pk"] = self.kwargs["pk"]
        return ctx


class SuplenteDeleteView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, suplente_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        suplente = get_object_or_404(CoordenadorSuplente, pk=suplente_id, nucleo=nucleo)
        suplente.delete()
        messages.success(request, _("Suplente removido."))
        return redirect("nucleos:detail", pk=pk)


class ExportarMembrosView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        formato = request.GET.get("formato", "csv")
        participacoes = nucleo.participacoes.select_related("user")
        now = timezone.now()
        suplentes = set(
            CoordenadorSuplente.objects.filter(
                nucleo=nucleo,
                periodo_inicio__lte=now,
                periodo_fim__gte=now,
                deleted=False,
            ).values_list("usuario_id", flat=True)
        )
        data = tablib.Dataset(
            headers=[
                "Nome",
                "Email",
                "Status",
                "papel",
                "is_suplente",
                "data_ingresso",
            ]
        )
        for p in participacoes:
            nome = p.user.get_full_name() or p.user.username
            data.append(
                [
                    nome,
                    p.user.email,
                    p.status,
                    p.papel,
                    p.user_id in suplentes,
                    (p.data_decisao or p.data_solicitacao).isoformat(),
                ]
            )
        notify_exportacao_membros.delay(nucleo.id)
        logger.info(
            "Exportação de membros",
            extra={"nucleo_id": nucleo.id, "user_id": request.user.id, "formato": formato},
        )
        if formato == "xls":
            response = HttpResponse(
                data.export("xlsx"),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f"attachment; filename=nucleo-{nucleo.id}-membros.xlsx"
            return response
        response = HttpResponse(data.export("csv"), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename=nucleo-{nucleo.id}-membros.csv"
        return response


class NucleoToggleActiveView(GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo.all_objects, pk=pk)
        if nucleo.deleted:
            nucleo.undelete()
        else:
            nucleo.soft_delete()
        return redirect("nucleos:list")
