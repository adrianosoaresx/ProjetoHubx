import factory
from factory.django import DjangoModelFactory
from .models import TokenAcesso
from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

class TokenAcessoFactory(DjangoModelFactory):
    class Meta:
        model = TokenAcesso

    usuario = factory.SubFactory(UserFactory)
    organizacao = factory.SubFactory(OrganizacaoFactory)
    tipo_destino = factory.Faker("random_element", elements=["admin", "gerente", "cliente"])
    estado = factory.Faker("random_element", elements=["novo", "usado", "expirado"])
    data_expiracao = factory.Faker("future_datetime", locale="pt_BR")

    @factory.post_generation
    def nucleos(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for nucleo in extracted:
                self.nucleos.add(nucleo)
        else:
            self.nucleos.add(NucleoFactory())
