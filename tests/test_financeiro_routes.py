import uuid
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import UserType
from financeiro.models import FinanceiroTaskLog


class FinanceiroRoutesTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="user@example.com", password="pass", user_type=UserType.ADMIN)
        self.client.force_login(self.user)

    def test_task_log_detail_route(self):
        log = FinanceiroTaskLog.objects.create(nome_tarefa="t", status="ok")
        url = reverse("financeiro:task_log_detail", kwargs={"pk": log.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_reprocessar_erros_route(self):
        url = reverse("financeiro_api:financeiro-reprocessar-erros", args=[uuid.uuid4()])
        file = SimpleUploadedFile("data.csv", b"id\n", content_type="text/csv")
        resp = self.client.post(url, {"file": file})
        self.assertEqual(resp.status_code, 404)
