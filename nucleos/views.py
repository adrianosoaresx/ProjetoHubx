from __future__ import annotations

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
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
from core.cache import get_cache_version
from core.permissions import AdminRequiredMixin, GerenteRequiredMixin, NoSuperadminMixin

from .forms import NucleoForm, NucleoSearchForm, ParticipacaoDecisaoForm, SuplenteForm
from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo
from .tasks import (
    notify_participacao_aprovada,
    notify_participacao_recusada,
    notify_suplente_designado,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class NucleoListView(NoSuperadminMixin, LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/list.html"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        q = self.request.GET.get("q", "")
        version = get_cache_version("nucleos_list")
        cache_key = f"nucleos_list:v{version}:{user.id}:{q}"
        cached_ids = cache.get(cache_key)

        base_qs = (
            Nucleo.objects.select_related("organizacao")
            .prefetch_related("participacoes")
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

        if cached_ids is not None:
            qs = base_qs.filter(pk__in=cached_ids).order_by("nome")
            return list(qs)

        qs = base_qs.filter(deleted=False)

        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        elif user.user_type in {UserType.ASSOCIADO, UserType.NUCLEADO}:
            qs = qs.filter(organizacao=user.organizacao)

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(slug__icontains=q))

        ids = list(qs.order_by("nome").distinct().values_list("pk", flat=True))
        cache.set(cache_key, ids, 300)

        return list(base_qs.filter(pk__in=ids).order_by("nome"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        return ctx


class NucleoMeusView(NoSuperadminMixin, LoginRequiredMixin, ListView):
    model = Nucleo
    template_name = "nucleos/meus_list.html"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        q = self.request.GET.get("q", "")
        version = get_cache_version("nucleos_meus")
        cache_key = f"nucleos_meus:v{version}:{user.id}:{q}"
        cached_ids = cache.get(cache_key)

        base_qs = (
            Nucleo.objects.select_related("organizacao")
            .prefetch_related("participacoes")
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

        if cached_ids is not None:
            qs = base_qs.filter(pk__in=cached_ids).order_by("nome")
            return list(qs)

        qs = base_qs.filter(
            deleted=False,
            participacoes__user=user,
            participacoes__status="ativo",
            participacoes__status_suspensao=False,
        )

        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(slug__icontains=q))

        ids = list(qs.order_by("nome").distinct().values_list("pk", flat=True))
        cache.set(cache_key, ids, 300)

        return list(base_qs.filter(pk__in=ids).order_by("nome"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = NucleoSearchForm(self.request.GET or None)
        return ctx


class NucleoCreateView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Nucleo
    form_class = NucleoForm
    template_name = "nucleos/create.html"
    success_url = reverse_lazy("nucleos:list")

    def form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, _("Núcleo criado com sucesso."))
        return super().form_valid(form)


class NucleoUpdateView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, UpdateView):
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


class NucleoDeleteView(NoSuperadminMixin, AdminRequiredMixin, LoginRequiredMixin, View):
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


class NucleoDetailView(NoSuperadminMixin, LoginRequiredMixin, DetailView):
    model = Nucleo
    template_name = "nucleos/detail.html"

    def get_queryset(self):
        qs = Nucleo.objects.filter(deleted=False).prefetch_related("participacoes__user", "coordenadores_suplentes")
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
        if self.request.user.user_type in {
            UserType.ADMIN,
            UserType.COORDENADOR,
        }:
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


class NucleoMetricsView(NoSuperadminMixin, LoginRequiredMixin, DetailView):
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


class SolicitarParticipacaoModalView(NoSuperadminMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        return render(request, "nucleos/solicitar_modal.html", {"nucleo": nucleo})


class PostarFeedModalView(NoSuperadminMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        return render(request, "nucleos/postar_modal.html", {"nucleo": nucleo})


class ConvitesModalView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
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
            },
        )


class ParticipacaoCreateView(NoSuperadminMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao, created = ParticipacaoNucleo.all_objects.get_or_create(user=request.user, nucleo=nucleo)

        save_fields: list[str] = []
        if participacao.deleted:
            participacao.deleted = False
            participacao.deleted_at = None
            save_fields += ["deleted", "deleted_at"]

        if not created and participacao.status != "pendente":
            participacao.status = "pendente"
            participacao.data_solicitacao = timezone.now()
            participacao.decidido_por = None
            participacao.data_decisao = None
            participacao.justificativa = ""
            save_fields += [
                "status",
                "data_solicitacao",
                "decidido_por",
                "data_decisao",
                "justificativa",
            ]
            messages.success(request, _("Solicitação reenviada."))
        else:
            messages.success(request, _("Solicitação enviada."))

        if save_fields:
            participacao.save(update_fields=save_fields)
        return redirect("nucleos:detail", pk=pk)


class ParticipacaoDecisaoView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, FormView):
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


class MembroRemoveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        participacao.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse("")
        messages.success(request, _("Membro removido do núcleo."))
        return redirect("nucleos:detail", pk=pk)


class MembroPromoverView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, participacao_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        participacao = get_object_or_404(ParticipacaoNucleo, pk=participacao_id, nucleo=nucleo)
        novo_papel = "membro" if participacao.papel == "coordenador" else "coordenador"
        participacao.papel = novo_papel
        participacao.save(update_fields=["papel"])
        if request.headers.get("HX-Request"):
            return render(
                request,
                "nucleos/partials/membro.html",
                {"part": participacao, "object": nucleo},
            )
        return redirect("nucleos:detail", pk=pk)


class SuplenteCreateView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, CreateView):
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


class SuplenteDeleteView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, suplente_id):
        nucleo = get_object_or_404(Nucleo, pk=pk, deleted=False)
        suplente = get_object_or_404(CoordenadorSuplente, pk=suplente_id, nucleo=nucleo)
        suplente.delete()
        messages.success(request, _("Suplente removido."))
        return redirect("nucleos:detail", pk=pk)


class NucleoToggleActiveView(NoSuperadminMixin, GerenteRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        nucleo = get_object_or_404(Nucleo.all_objects, pk=pk)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        if nucleo.deleted:
            nucleo.undelete()
        else:
            nucleo.soft_delete()
        return redirect("nucleos:list")
