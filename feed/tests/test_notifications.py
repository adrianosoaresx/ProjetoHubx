from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class FeedNotificationTest(TestCase):
    def setUp(self) -> None:
        org = OrganizacaoFactory()
        self.user = UserFactory(organizacao=org)
        self.other = UserFactory(organizacao=org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("feed.tasks.enviar_para_usuario")
    def test_notify_new_post_once(self, enviar) -> None:
        res = self.client.post(
            "/api/feed/posts/",
            {"conteudo": "ola", "tipo_feed": "global"},
        )
        self.assertEqual(res.status_code, 201)
        post_id = res.data["id"]
        self.assertEqual(enviar.call_count, 1)
        from feed.tasks import notify_new_post

        notify_new_post(post_id)
        self.assertEqual(enviar.call_count, 1)  # idempotente

