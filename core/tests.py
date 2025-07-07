from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model

from nucleos.models import Nucleo
from empresas.models import Empresa
from eventos.models import Evento


class GenerateTestDataCommandTests(TestCase):
    """Tests for the ``generate_test_data`` management command."""

    def test_generated_counts_and_passwords(self):
        """Command creates the expected objects and passwords."""
        call_command("generate_test_data")

        User = get_user_model()

        # 115 new users + 1 root superuser from migrations
        self.assertEqual(User.objects.count(), 116)
        self.assertEqual(Nucleo.objects.count(), 20)
        self.assertEqual(Empresa.objects.count(), 150)
        self.assertEqual(Evento.objects.count(), 10)

        # All generated users (non superusers) should have an empty password
        passwords = (
            User.objects.exclude(is_superuser=True)
            .values_list("password", flat=True)
            .distinct()
        )
        self.assertEqual(list(passwords), [""])

    def test_root_has_connections(self):
        """Root user should be connected to all generated users."""
        call_command("generate_test_data")

        User = get_user_model()
        root_user = User.objects.get(username="root")
        self.assertEqual(
            set(root_user.connections.values_list("id", flat=True)),
            set(User.objects.exclude(is_superuser=True).values_list("id", flat=True)),
        )

        root_user = User.objects.get(username="root")
        self.assertEqual(
            root_user.connections.count(),
            User.objects.filter(is_superuser=False).count(),
        )
