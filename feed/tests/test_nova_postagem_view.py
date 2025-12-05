from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory


class NovaPostagemViewTest(TestCase):
    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    @patch("feed.tasks.POSTS_CREATED.inc")
    @patch("feed.tasks.notify_new_post.delay")
    def test_redirect_to_locked_nucleo_feed(self, mock_notify, mock_inc):
        organizacao = OrganizacaoFactory()
        nucleo = NucleoFactory(organizacao=organizacao)
        user = UserFactory(organizacao=organizacao)
        user.user_type = UserType.ADMIN
        user.save()

        self.client.force_login(user)
        data = {
            "tipo_feed": "nucleo",
            "nucleo": str(nucleo.id),
            "organizacao": str(organizacao.id),
            "conteudo": "Olá núcleo",
        }

        response = self.client.post(reverse("feed:nova_postagem"), data)

        expected_url = f"{reverse('feed:listar')}?tipo_feed=nucleo&nucleo={nucleo.id}"
        self.assertRedirects(response, expected_url)
        mock_inc.assert_called_once_with()
        mock_notify.assert_called_once()
