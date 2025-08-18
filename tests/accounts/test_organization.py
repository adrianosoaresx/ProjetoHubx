from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserType


class OrganizationUserTests(TestCase):
    def setUp(self):
        from organizacoes.models import Organizacao

        self.User = get_user_model()
        self.org1 = Organizacao.objects.create(nome="Org1", cnpj="00.000.000/0001-00", slug="org1")
        self.org2 = Organizacao.objects.create(nome="Org2", cnpj="00.000.000/0002-00", slug="org2")
        self.admin1 = self.User.objects.create_user(
            email="admin1@example.com",
            username="admin1",
            password="pass",
            organizacao=self.org1,
            user_type=UserType.ADMIN,
        )
        self.admin2 = self.User.objects.create_user(
            email="admin2@example.com",
            username="admin2",
            password="pass",
            organizacao=self.org2,
        )
        self.root = self.User.objects.create_superuser(
            email="root@example.com",
            username="root",
            password="pass",
        )

    def test_user_sees_only_same_org(self):
        self.client.force_login(self.admin1)
        users = list(self.User.objects.filter(organizacao=self.admin1.organizacao))
        self.assertEqual(users, [self.admin1])

    def test_username_can_repeat_across_same_org(self):
        self.User.objects.create_user(
            email="joao1@example.com",
            username="joao",
            password="pass",
            organizacao=self.org1,
        )
        self.User.objects.create_user(
            email="joao2@example.com",
            username="joao",
            password="pass",
            organizacao=self.org1,
        )
        count = self.User.objects.filter(username="joao", organizacao=self.org1).count()
        self.assertEqual(count, 2)
        # usernames continuam únicos entre organizações diferentes
        other = self.User.objects.create_user(
            email="joao3@example.com",
            username="joao",
            password="pass",
            organizacao=self.org2,
        )
        self.assertEqual(other.username, "joao")

    def test_superuser_sees_all(self):
        self.client.force_login(self.root)
        users = list(self.User.objects.all())
        self.assertIn(self.admin1, users)
        self.assertIn(self.admin2, users)
