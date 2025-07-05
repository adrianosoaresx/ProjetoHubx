from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from .models import NotificationSettings, UserMedia, TokenAcesso


class RegistrationSessionTests(TestCase):
    """Ensure each etapa do cadastro armazena valores na sessao."""

    def setUp(self):
        self.client = Client()
        self.creator = get_user_model().objects.create_user(
            username="creator", password="pass"
        )
        self.token = TokenAcesso.objects.create(
            gerado_por=self.creator,
            tipo_destino=TokenAcesso.Tipo.CLIENTE,
        )

    def test_registration_flow_populates_session(self):
        """Percorre o fluxo de registro verificando a sessao a cada passo."""

        # Step 1: token
        response = self.client.post(
            reverse("accounts:token"), {"token": self.token.codigo}, follow=True
        )
        self.assertIn("invite_token", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:usuario"))

        # Step 2: usuario
        response = self.client.post(
            reverse("accounts:usuario"), {"usuario": "newuser"}, follow=True
        )
        self.assertIn("usuario", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:nome"))

        # Step 3: nome
        response = self.client.post(
            reverse("accounts:nome"), {"nome": "Test User"}, follow=True
        )
        self.assertIn("nome", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:cpf"))

        # Step 4: cpf
        response = self.client.post(
            reverse("accounts:cpf"), {"cpf": "123.456.789-09"}, follow=True
        )
        self.assertIn("cpf", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:email"))
        # Step 5: email
        response = self.client.post(
            reverse("accounts:email"), {"email": "test@example.com"}, follow=True
        )
        self.assertIn("email", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:senha"))

        # Step 6: senha
        response = self.client.post(
            reverse("accounts:senha"),
            {"senha": "abc12345", "confirmar_senha": "abc12345"},
            follow=True,
        )
        self.assertNotIn("senha", self.client.session)
        self.assertIn("senha_hash", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:foto"))

        # Step 7: foto
        image = SimpleUploadedFile(
            "test.jpg", b"filecontent", content_type="image/jpeg"
        )
        response = self.client.post(
            reverse("accounts:foto"), {"foto": image}, follow=True
        )
        self.assertIn("foto", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:termos"))

        # Step 8: termos
        response = self.client.post(
            reverse("accounts:termos"), {"aceitar_termos": "on"}, follow=False
        )
        self.assertIn("termos", self.client.session)
        self.assertEqual(response.url, reverse("accounts:perfil"))

        user = get_user_model().objects.get(username="newuser")
        self.assertTrue(NotificationSettings.objects.filter(user=user).exists())


class RegisterViewTests(TestCase):
    """Verifica a criacao de NotificationSettings no fluxo simples."""

    def setUp(self):
        self.client = Client()

    def test_signal_creates_notification_settings(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "janedoe",
                "email": "jane@example.com",
                "password1": "Complexpass123",
                "password2": "Complexpass123",
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="janedoe")
        self.assertTrue(NotificationSettings.objects.filter(user=user).exists())


class MediaUploadTests(TestCase):
    """Testa o upload e listagem de mídias do usuário."""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="midiauser", password="pass"
        )
        self.client.force_login(self.user)

    def test_media_is_listed_after_upload(self):
        file = SimpleUploadedFile("doc.txt", b"content")
        response = self.client.post(reverse("accounts:midias"), {"file": file})
        self.assertEqual(response.status_code, 302)
        media = UserMedia.objects.get(user=self.user)

        response = self.client.get(reverse("accounts:midias"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(media.file.name, response.content.decode())

    def test_media_edit(self):
        media = UserMedia.objects.create(
            user=self.user,
            file=SimpleUploadedFile("doc.txt", b"content"),
            descricao="old",
        )
        response = self.client.post(
            reverse("accounts:midia_edit", args=[media.pk]),
            {"descricao": "new"},
        )
        self.assertEqual(response.status_code, 302)
        media.refresh_from_db()
        self.assertEqual(media.descricao, "new")

    def test_media_delete(self):
        media = UserMedia.objects.create(
            user=self.user,
            file=SimpleUploadedFile("doc.txt", b"content"),
        )
        response = self.client.post(reverse("accounts:midia_delete", args=[media.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserMedia.objects.filter(pk=media.pk).exists())
