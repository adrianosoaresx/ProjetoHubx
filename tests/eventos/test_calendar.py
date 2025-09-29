from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import make_aware
from django.utils.formats import date_format

from accounts.models import UserType
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


class CalendarViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="pass",
            user_type=UserType.ADMIN,
            organizacao=self.org,
        )

    def test_calendar_pt_br_renders(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("eventos:calendario"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, date.today().strftime("%Y"))

    def test_evento_novo_requires_login_and_permission(self):
        url = reverse("eventos:evento_novo")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        User = get_user_model()
        client_user = User.objects.create_user(
            email="cliente@example.com",
            username="cliente",
            password="pass",
            user_type=UserType.NUCLEADO,
        )
        self.client.force_login(client_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_htmx_day_click_returns_events(self):
        self.client.force_login(self.admin)
        dia = date.today()
        evento = Evento.objects.create(
            organizacao=self.org,
            titulo="Evento",
            data_inicio=make_aware(datetime.combine(dia, datetime.min.time())),
            data_fim=make_aware(datetime.combine(dia, datetime.min.time()) + timedelta(hours=1)),
            status=Evento.Status.ATIVO,
            publico_alvo=0,
            numero_convidados=10,
            numero_presentes=0,
            local="Rua X",
            cidade="Cidade",
            estado="ST",
            cep="12345-678",
            coordenador=self.admin,
            contato_nome="Admin",
        )
        InscricaoEvento.objects.create(evento=evento, user=self.admin, status="confirmada")
        resp = self.client.get(
            reverse("eventos:lista_eventos", args=[dia.isoformat()]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Evento")
        data_formatada = date_format(dia, format="SHORT_DATE_FORMAT")
        self.assertContains(resp, f"Eventos de {data_formatada}")

    def test_month_navigation_context(self):
        url = reverse("eventos:calendario_mes", args=[2025, 5])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["data_atual"], date(2025, 5, 1))
        self.assertIn("prev_ano", resp.context)
        self.assertIn("next_ano", resp.context)

    def test_root_cannot_create_event(self):
        User = get_user_model()
        root = User.objects.create_superuser(
            email="root@example.com",
            username="root",
            password="pass",
        )
        self.client.force_login(root)
        resp = self.client.get(reverse("eventos:evento_novo"))
        self.assertEqual(resp.status_code, 403)

    def test_calendar_displays_month_in_portuguese(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("eventos:calendario"))
        month_name = date_format(date.today(), "F")
        self.assertContains(resp, month_name)
