from django.test import TestCase
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

from membros.templatetags.membros_extras import usuario_tipo_badge


class MembroPromoverFormViewDemotionTests(TestCase):
    def setUp(self):
        self.organizacao = OrganizacaoFactory()
        self.admin = UserFactory(
            organizacao=self.organizacao,
            user_type=UserType.ADMIN.value,
        )
        self.admin.nucleo = None
        self.admin.save(update_fields=["nucleo"])
        self.client.force_login(self.admin)

    def test_demotes_to_associado_after_removing_last_roles(self):
        nucleo = NucleoFactory(organizacao=self.organizacao)
        membro = UserFactory(
            organizacao=self.organizacao,
            user_type=UserType.CONSULTOR.value,
        )
        membro.nucleo = None
        membro.save(update_fields=["nucleo", "user_type"])

        nucleo.consultor = membro
        nucleo.save(update_fields=["consultor"])

        url = reverse("membros:membro_promover_form", args=[membro.pk])
        response = self.client.post(
            url,
            {"remover_consultor_nucleos": [str(nucleo.pk)]},
        )

        self.assertEqual(response.status_code, 200)
        membro.refresh_from_db()
        self.assertEqual(membro.user_type, UserType.ASSOCIADO.value)

        tipo_badge = usuario_tipo_badge(membro)
        self.assertIsNotNone(tipo_badge)
        self.assertEqual(tipo_badge["label"], UserType.ASSOCIADO.label)
        self.assertEqual(tipo_badge["type"], UserType.ASSOCIADO.value)
