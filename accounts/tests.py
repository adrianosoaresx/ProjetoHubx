from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile


class RegistrationSessionTests(TestCase):
    """Ensure each etapa do cadastro armazena valores na sessao."""

    def setUp(self):
        self.client = Client()

    def test_registration_flow_populates_session(self):
        """Percorre o fluxo de registro verificando a sessao a cada passo."""

        # Step 1: token
        response = self.client.post(
            reverse("accounts:token"), {"token": "abc"}, follow=True
        )
        self.assertIn("invite_token", self.client.session)
        self.assertEqual(
            response.redirect_chain[-1][0], reverse("accounts:usuario")
        )

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
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:email"))

        # Step 4: email
        response = self.client.post(
            reverse("accounts:email"), {"email": "test@example.com"}, follow=True
        )
        self.assertIn("email", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:senha"))

        # Step 5: senha
        response = self.client.post(
            reverse("accounts:senha"),
            {"senha1": "abc12345", "senha2": "abc12345"},
            follow=True,
        )
        self.assertIn("senha", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:foto"))

        # Step 6: foto
        image = SimpleUploadedFile("test.jpg", b"filecontent", content_type="image/jpeg")
        response = self.client.post(
            reverse("accounts:foto"), {"foto": image}, follow=True
        )
        self.assertIn("foto", self.client.session)
        self.assertEqual(response.redirect_chain[-1][0], reverse("accounts:termos"))

        # Step 7: termos
        response = self.client.post(
            reverse("accounts:termos"), {"aceitar_termos": "on"}, follow=False
        )
        self.assertIn("termos", self.client.session)
        self.assertEqual(response.url, reverse("perfil"))
