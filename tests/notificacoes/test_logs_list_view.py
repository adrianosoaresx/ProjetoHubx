import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.forms import NotificationLogFilterForm
from notificacoes.models import Canal, NotificationLog, NotificationStatus, NotificationTemplate


pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_user():
    user = UserFactory()
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


def test_list_logs_renders_form(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("notificacoes:logs_list"))

    assert response.status_code == 200
    assert "form" in response.context
    assert isinstance(response.context["form"], NotificationLogFilterForm)


def test_list_logs_applies_filters(client, staff_user):
    client.force_login(staff_user)

    template_email = NotificationTemplate.objects.create(
        codigo="tpl-email",
        assunto="Assunto",
        corpo="Corpo",
        canal=Canal.EMAIL,
    )
    template_push = NotificationTemplate.objects.create(
        codigo="tpl-push",
        assunto="Assunto",
        corpo="Corpo",
        canal=Canal.PUSH,
    )

    matching_log = NotificationLog.objects.create(
        user=staff_user,
        template=template_email,
        canal=Canal.EMAIL,
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )
    NotificationLog.objects.create(
        user=staff_user,
        template=template_push,
        canal=Canal.PUSH,
        status=NotificationStatus.FALHA,
        data_envio=timezone.now() - timezone.timedelta(days=7),
    )

    url = reverse("notificacoes:logs_list")
    filters = {
        "inicio": matching_log.data_envio.date().isoformat(),
        "canal": Canal.EMAIL,
        "status": NotificationStatus.ENVIADA,
        "template": template_email.codigo,
    }
    response = client.get(url, filters)

    assert response.status_code == 200
    page_obj = response.context["logs"]
    assert list(page_obj) == [matching_log]

    form = response.context["form"]
    assert form.is_bound
    assert form.is_valid()
    assert form.cleaned_data["template"] == template_email
