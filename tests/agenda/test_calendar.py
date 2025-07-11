from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizacoes.models import Organizacao
from agenda.models import Evento


class CalendarViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.admin = User.objects.create_user(
            "admin", password="pass", tipo_id=User.Tipo.ADMIN, organizacao=self.org
        )

    def test_calendar_pt_br_renders(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("agenda:calendario"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, date.today().strftime("%Y"))

    def test_evento_novo_requires_login_and_permission(self):
        url = reverse("agenda:evento_novo")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        User = get_user_model()
        client_user = User.objects.create_user("cliente", password="pass", tipo_id=User.Tipo.CLIENTE)
        self.client.force_login(client_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_htmx_day_click_returns_events(self):
        self.client.force_login(self.admin)
        dia = date.today()
        Evento.objects.create(
            organizacao=self.org,
            titulo="Evento",
            data_hora=datetime.combine(dia, datetime.min.time()),
            duracao=timedelta(hours=1),
        )
        resp = self.client.get(
            reverse("agenda:lista_eventos", args=[dia.isoformat()]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Evento")

    def test_month_navigation_context(self):
        url = reverse("agenda:calendario_mes", args=[2025, 5])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["data_atual"], date(2025, 5, 1))
        self.assertIn("prev_ano", resp.context)
        self.assertIn("next_ano", resp.context)

