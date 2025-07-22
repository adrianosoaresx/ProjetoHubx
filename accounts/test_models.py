from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User, UserType
from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from tokens.models import TokenAcesso

from .models import NotificationSettings, UserMedia
class RegistrationSessionTests(TestCase):
    """Fluxo de registro sera reavaliado."""

    def test_placeholder(self):
        assert True





class RegisterViewTests(TestCase):
    """Verifica a criacao de NotificationSettings no fluxo simples."""

    def setUp(self):
        self.client = Client()

    def test_signal_creates_notification_settings(self):
        user = get_user_model().objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password="Complexpass123",
        )
        self.assertTrue(NotificationSettings.objects.filter(user=user).exists())


class MediaUploadTests(TestCase):
    """Testa o upload e listagem de mídias do usuário."""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="midiauser",
            email="midia@example.com",
            password="pass",
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


class UserModelTests(TestCase):
    def setUp(self):
        self.organizacao = Organizacao.objects.create(nome="Org Teste")
        self.nucleo = Nucleo.objects.create(nome="Núcleo Teste", organizacao=self.organizacao)
        self.user_root = get_user_model().objects.create_superuser(
            username="root",
            email="root@example.com",
            password="pass",
        )
        self.user_admin = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="pass",
            is_staff=True,
            organizacao=self.organizacao,
        )
        self.user_coordenador = get_user_model().objects.create_user(
            username="coordenador",
            email="coord@example.com",
            password="pass",
            is_associado=True,
            is_coordenador=True,
            nucleo=self.nucleo,
            organizacao=self.organizacao,
        )

    def test_get_tipo_usuario(self):
        self.assertEqual(self.user_root.get_tipo_usuario, UserType.ROOT.value)
        self.assertEqual(self.user_admin.get_tipo_usuario, UserType.ADMIN.value)
        self.assertEqual(
            self.user_coordenador.get_tipo_usuario, UserType.COORDENADOR.value
        )

    def test_criacao_usuario_validacoes(self):
        user = get_user_model().objects.create_user(
            username="invalid",
            email="invalid@example.com",
            password="pass",
            organizacao=None,
        )
        self.assertIsNone(user.organizacao)

    def test_escopo_organizacao(self):
        users = get_user_model().objects.filter(organizacao=self.organizacao)
        self.assertIn(self.user_admin, users)
        self.assertIn(self.user_coordenador, users)
        self.assertNotIn(self.user_root, users)


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="password123",
            username="testuser",
            user_type=UserType.ADMIN,
        )

    def test_user_creation(self):
        """Testa se o usuário é criado corretamente."""
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.check_password("password123"))

    def test_user_type(self):
        """Testa se o tipo de usuário está associado corretamente."""
        self.assertEqual(self.user.user_type, UserType.ADMIN.value)

    def test_user_permissions(self):
        """Admins devem ser staff por padrão."""
        self.assertTrue(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)


class UserTypeModelTest(TestCase):
    def test_user_type_creation(self):
        """Testa a criação de um tipo de usuário."""
        user_type = UserType.ADMIN.value
        self.assertEqual(user_type, "admin")
