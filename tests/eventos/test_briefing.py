import os
from datetime import timedelta

import django
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from accounts.models import UserType  # noqa: E402
from eventos.forms import BriefingEventoForm, BriefingTemplateForm  # noqa: E402
from eventos.models import BriefingEvento, BriefingTemplate, Evento  # noqa: E402
from organizacoes.models import Organizacao  # noqa: E402


def _create_organizacao() -> Organizacao:
    return Organizacao.objects.create(nome="Org", cnpj="12345678000195")


def _create_evento(organizacao: Organizacao) -> Evento:
    inicio = timezone.now() + timedelta(days=2)
    return Evento.objects.create(
        titulo="Evento",
        slug="evento",
        descricao="Descricao",
        data_inicio=inicio,
        data_fim=inicio + timedelta(hours=2),
        local="Local",
        cidade="Cidade",
        estado="SP",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        gratuito=True,
    )


@pytest.mark.django_db
def test_briefing_template_form_validates_estrutura_json() -> None:
    form = BriefingTemplateForm(
        data={
            "nome": "Template",
            "descricao": "",
            "estrutura": {"label": "Nome"},
            "ativo": True,
        }
    )

    assert not form.is_valid()
    assert "estrutura" in form.errors

    form = BriefingTemplateForm(
        data={
            "nome": "Template",
            "descricao": "",
            "estrutura": [
                {"label": "Nome", "type": "text", "required": True},
                {"label": "Tipo", "type": "select", "required": False, "options": ["A", "B"]},
            ],
            "ativo": True,
        }
    )

    assert form.is_valid()


@pytest.mark.django_db
def test_briefing_evento_form_builds_dynamic_fields_and_saves_respostas() -> None:
    organizacao = _create_organizacao()
    evento = _create_evento(organizacao)
    template = BriefingTemplate.objects.create(
        nome="Template",
        descricao="",
        estrutura=[
            {"label": "Nome", "type": "text", "required": True},
            {"label": "Tipo", "type": "select", "required": False, "options": ["A", "B"]},
        ],
    )
    briefing = BriefingEvento.objects.create(
        evento=evento,
        template=template,
        respostas={"Nome": "Joana", "Tipo": "A"},
    )

    form = BriefingEventoForm(instance=briefing, template=template)
    assert "pergunta_1" in form.fields
    assert "pergunta_2" in form.fields
    assert form.initial["pergunta_1"] == "Joana"
    assert form.fields["pergunta_2"].choices == [("A", "A"), ("B", "B")]

    form = BriefingEventoForm(
        data={"pergunta_1": "Maria", "pergunta_2": "B"},
        instance=briefing,
        template=template,
    )
    assert form.is_valid()
    updated = form.save()
    assert updated.respostas == {"Nome": "Maria", "Tipo": "B"}


@pytest.mark.django_db
def test_briefing_evento_status_transitions_validate() -> None:
    organizacao = _create_organizacao()
    evento = _create_evento(organizacao)
    template = BriefingTemplate.objects.create(nome="Template", descricao="", estrutura=[])
    briefing = BriefingEvento.objects.create(evento=evento, template=template)
    User = get_user_model()
    usuario = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="senha123",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )

    briefing.enviar_orcamento(usuario)
    briefing.refresh_from_db()
    assert briefing.status == BriefingEvento.Status.ORCAMENTADO
    assert briefing.orcamento_enviado_por == usuario

    briefing.aprovar(usuario)
    briefing.refresh_from_db()
    assert briefing.status == BriefingEvento.Status.APROVADO
    assert briefing.aprovado_por == usuario

    novo_evento = _create_evento(organizacao)
    briefing = BriefingEvento.objects.create(evento=novo_evento, template=template)
    with pytest.raises(ValidationError):
        briefing.aprovar(usuario)
    with pytest.raises(ValidationError):
        briefing.enviar_orcamento(None)


@pytest.mark.django_db
def test_briefing_select_view_permissions_and_creation() -> None:
    organizacao = _create_organizacao()
    evento = _create_evento(organizacao)
    template = BriefingTemplate.objects.create(nome="Template", descricao="", estrutura=[])
    User = get_user_model()
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="senha123",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )
    associado = User.objects.create_user(
        username="associado",
        email="assoc@example.com",
        password="senha123",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )

    client = Client()
    client.force_login(associado)
    response = client.get(
        reverse("eventos:briefing_selecionar", kwargs={"evento_id": evento.pk})
    )
    assert response.status_code == 403

    client.force_login(admin)
    response = client.post(
        reverse("eventos:briefing_selecionar", kwargs={"evento_id": evento.pk}),
        data={"template": template.pk},
    )
    assert response.status_code == 302
    briefing = BriefingEvento.objects.get(evento=evento)
    assert briefing.template == template
    assert reverse("eventos:briefing_preencher", kwargs={"evento_id": evento.pk}) in response[
        "Location"
    ]


@pytest.mark.django_db
def test_briefing_template_views_reject_coordenador() -> None:
    organizacao = _create_organizacao()
    template = BriefingTemplate.objects.create(nome="Template", descricao="", estrutura=[])
    User = get_user_model()
    coordenador = User.objects.create_user(
        username="coordenador",
        email="coord@example.com",
        password="senha123",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )

    client = Client()
    client.force_login(coordenador)

    response = client.get(reverse("eventos:briefing_template_list"))
    assert response.status_code == 403

    response = client.get(reverse("eventos:briefing_template_create"))
    assert response.status_code == 403

    response = client.get(reverse("eventos:briefing_template_update", kwargs={"pk": template.pk}))
    assert response.status_code == 403

    response = client.get(reverse("eventos:briefing_template_delete", kwargs={"pk": template.pk}))
    assert response.status_code == 403
