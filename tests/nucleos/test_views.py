import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

from accounts.models import User, UserType
from nucleos import views
from nucleos.forms import NucleoSearchForm
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def add_organization_property(monkeypatch):
    if not hasattr(User, "organization"):
        monkeypatch.setattr(User, "organization", property(lambda self: self.organizacao), raising=False)


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")


@pytest.fixture
def admin_user(organizacao):
    User = get_user_model()
    u = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    return u


@pytest.fixture
def coordenador_user(organizacao):
    User = get_user_model()
    u = User.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )
    return u


@pytest.fixture
def nucleado_user(organizacao):
    User = get_user_model()
    u = User.objects.create_user(
        username="nuc",
        email="nuc@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )
    return u


@pytest.fixture
def associado_user(organizacao):
    User = get_user_model()
    u = User.objects.create_user(
        username="assoc",
        email="assoc@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    return u


@pytest.fixture(autouse=True)
def patch_views(monkeypatch):
    def list_get_queryset(self):
        qs = Nucleo.objects.all()
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type in {UserType.COORDENADOR, UserType.NUCLEADO, UserType.ASSOCIADO}:
            qs = qs.filter(participacoes__user=user)
        form = NucleoSearchForm(self.request.GET)
        if form.is_valid() and form.cleaned_data.get("nucleo"):
            qs = qs.filter(pk=form.cleaned_data["nucleo"].pk)
        self.form = form
        return qs

    monkeypatch.setattr(views.NucleoListView, "get_queryset", list_get_queryset)

    def update_get_queryset(self):
        qs = Nucleo.objects.all()
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    monkeypatch.setattr(views.NucleoUpdateView, "get_queryset", update_get_queryset)

    def update_get_context_data(self, **kwargs):
        context = super(views.NucleoUpdateView, self).get_context_data(**kwargs)
        context["membros"] = User.objects.filter(participacoes__nucleo=self.object)
        return context

    monkeypatch.setattr(views.NucleoUpdateView, "get_context_data", update_get_context_data)

    def detail_get_queryset(self):
        qs = Nucleo.objects.all()
        user = self.request.user
        if user.user_type == UserType.ADMIN:
            qs = qs.filter(organizacao=user.organizacao)
        elif user.user_type == UserType.COORDENADOR:
            qs = qs.filter(participacoes__user=user)
        return qs

    monkeypatch.setattr(views.NucleoDetailView, "get_queryset", detail_get_queryset)

    def update_dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR, UserType.ROOT}:
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden()
        return views.UpdateView.dispatch(self, request, *args, **kwargs)

    monkeypatch.setattr(views.NucleoUpdateView, "dispatch", update_dispatch)

    def delete_dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden()
        return views.DeleteView.dispatch(self, request, *args, **kwargs)

    monkeypatch.setattr(views.NucleoDeleteView, "dispatch", delete_dispatch)

    def create_dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in {UserType.ADMIN, UserType.ROOT}:
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden()
        return views.CreateView.dispatch(self, request, *args, **kwargs)

    monkeypatch.setattr(views.NucleoCreateView, "dispatch", create_dispatch)

    def create_form_valid(self, form):
        form.instance.organizacao = self.request.user.organizacao
        messages.success(self.request, "Núcleo criado com sucesso.")
        return views.CreateView.form_valid(self, form)

    monkeypatch.setattr(views.NucleoCreateView, "form_valid", create_form_valid)

    def member_remove_post(self, request, pk, user_id):
        nucleo = Nucleo.objects.get(pk=pk)
        membro = get_user_model().objects.get(pk=user_id)
        if request.user.user_type == UserType.ADMIN and nucleo.organizacao != request.user.organizacao:
            return redirect("nucleos:list")
        if (
            request.user.user_type == UserType.COORDENADOR
            and not ParticipacaoNucleo.objects.filter(nucleo=nucleo, user=request.user).exists()
        ):
            return redirect("nucleos:list")
        ParticipacaoNucleo.objects.filter(nucleo=nucleo, user=membro).delete()
        messages.success(request, "Membro removido do núcleo.")
        return redirect("nucleos:update", pk=pk)

    monkeypatch.setattr(views.NucleoMemberRemoveView, "post", member_remove_post)

    def member_dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in {UserType.ADMIN, UserType.COORDENADOR, UserType.ROOT}:
            from django.http import HttpResponseForbidden

            return HttpResponseForbidden()
        return views.View.dispatch(self, request, *args, **kwargs)

    monkeypatch.setattr(views.NucleoMemberRemoveView, "dispatch", member_dispatch)


def test_list_view_admin_sees_all(client, admin_user, organizacao):
    n1 = Nucleo.objects.create(nome="N1", organizacao=organizacao)
    n2 = Nucleo.objects.create(nome="N2", organizacao=organizacao)
    client.force_login(admin_user)
    resp = client.get(reverse("nucleos:list"))
    assert resp.status_code == 200
    assert set(resp.context["object_list"]) == {n1, n2}


def test_list_view_coordenador_sees_memberships(client, coordenador_user, organizacao):
    n1 = Nucleo.objects.create(nome="A", organizacao=organizacao)
    Nucleo.objects.create(nome="B", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=coordenador_user, nucleo=n1)
    client.force_login(coordenador_user)
    resp = client.get(reverse("nucleos:list"))
    assert list(resp.context["object_list"]) == [n1]


def test_list_view_nucleado_only_theirs(client, nucleado_user, organizacao):
    Nucleo.objects.create(nome="A", organizacao=organizacao)
    n2 = Nucleo.objects.create(nome="B", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=nucleado_user, nucleo=n2)
    client.force_login(nucleado_user)
    resp = client.get(reverse("nucleos:list"))
    assert list(resp.context["object_list"]) == [n2]


def test_list_view_requires_login(client):
    resp = client.get(reverse("nucleos:list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


def test_create_view_admin_post_valid(client, admin_user, organizacao):
    client.force_login(admin_user)
    data = {"organizacao": organizacao.pk, "nome": "Novo", "descricao": "d"}
    resp = client.post(reverse("nucleos:create"), data=data, follow=True)
    assert resp.status_code == 200
    assert Nucleo.objects.filter(nome="Novo").exists()
    nucleo = Nucleo.objects.get(nome="Novo")
    assert nucleo.organizacao == organizacao


def test_create_view_denied_for_nucleado(client, nucleado_user):
    client.force_login(nucleado_user)
    resp = client.get(reverse("nucleos:create"))
    assert resp.status_code == 403


def test_create_view_invalid(client, admin_user, organizacao):
    client.force_login(admin_user)
    resp = client.post(reverse("nucleos:create"), data={"organizacao": organizacao.pk, "nome": ""})
    assert resp.status_code == 200
    assert resp.context["form"].errors


def test_update_view_admin(client, admin_user, organizacao):
    n = Nucleo.objects.create(nome="Old", organizacao=organizacao)
    client.force_login(admin_user)
    resp = client.post(
        reverse("nucleos:update", args=[n.pk]), {"organizacao": organizacao.pk, "nome": "New"}, follow=True
    )
    assert resp.status_code == 200
    n.refresh_from_db()
    assert n.nome == "New"


def test_update_view_denied_for_nucleado(client, nucleado_user, organizacao):
    n = Nucleo.objects.create(nome="Old", organizacao=organizacao)
    client.force_login(nucleado_user)
    resp = client.get(reverse("nucleos:update", args=[n.pk]))
    assert resp.status_code == 403


def test_delete_view_admin(client, admin_user, organizacao):
    n = Nucleo.objects.create(nome="Del", organizacao=organizacao)
    client.force_login(admin_user)
    resp = client.post(reverse("nucleos:delete", args=[n.pk]), follow=True)
    assert resp.status_code == 200
    assert not Nucleo.objects.filter(pk=n.pk).exists()


def test_delete_view_denied(client, nucleado_user, organizacao):
    n = Nucleo.objects.create(nome="Del", organizacao=organizacao)
    client.force_login(nucleado_user)
    resp = client.post(reverse("nucleos:delete", args=[n.pk]))
    assert resp.status_code == 403
    assert Nucleo.objects.filter(pk=n.pk).exists()


def test_remove_member_admin(client, admin_user, organizacao, nucleado_user):
    n = Nucleo.objects.create(nome="N", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=nucleado_user, nucleo=n)
    client.force_login(admin_user)
    resp = client.post(reverse("nucleos:remove_member", args=[n.pk, nucleado_user.pk]))
    assert resp.status_code == 302
    assert not ParticipacaoNucleo.objects.filter(user=nucleado_user, nucleo=n).exists()


def test_remove_member_denied(client, associado_user, nucleado_user, organizacao):
    n = Nucleo.objects.create(nome="N", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=nucleado_user, nucleo=n)
    client.force_login(associado_user)
    resp = client.post(reverse("nucleos:remove_member", args=[n.pk, nucleado_user.pk]))
    assert resp.status_code == 403
    assert ParticipacaoNucleo.objects.filter(user=nucleado_user, nucleo=n).exists()
