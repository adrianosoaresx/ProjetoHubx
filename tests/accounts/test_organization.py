from django.test import TestCase
from django.contrib.auth import get_user_model


class OrganizationUserTests(TestCase):
    def setUp(self):
        from organizacoes.models import Organizacao

        self.User = get_user_model()
        self.org1 = Organizacao.objects.create(nome="Org1", cnpj="00.000.000/0001-00")
        self.org2 = Organizacao.objects.create(nome="Org2", cnpj="00.000.000/0002-00")
        self.admin1 = self.User.objects.create_user(
            email="admin1@example.com",
            username="admin1",
            password="pass",
            organization=self.org1,
        )
        self.admin2 = self.User.objects.create_user(
            email="admin2@example.com",
            username="admin2",
            password="pass",
            organization=self.org2,
        )
        self.root = self.User.objects.get(username="root")

    def test_user_sees_only_same_org(self):
        self.client.force_login(self.admin1)
        users = list(self.User.objects.filter_current_org(self.admin1.organization))
        self.assertEqual(users, [self.admin1])

    def test_unique_username_per_organization(self):
        self.User.objects.create_user(
            email="joao1@example.com",
            username="joao",
            password="pass",
            organization=self.org1,
        )
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.User.objects.create_user(
                    email="joao2@example.com",
                    username="joao",
                    password="pass",
                    organization=self.org1,
                )
        self.User.objects.create_user(
            email="joao3@example.com",
            username="joao",
            password="pass",
            organization=self.org2,
        )

    def test_superuser_sees_all(self):
        self.client.force_login(self.root)
        users = list(self.User.objects.all())
        self.assertIn(self.admin1, users)
        self.assertIn(self.admin2, users)
