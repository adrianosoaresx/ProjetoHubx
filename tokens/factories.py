import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

from .models import TokenAcesso


class TokenAcessoFactory(DjangoModelFactory):
    class Meta:
        model = TokenAcesso

    gerado_por = factory.SubFactory(UserFactory)
    usuario = factory.SubFactory(UserFactory)
    organizacao = factory.SubFactory(OrganizacaoFactory)
    tipo_destino = factory.Faker(
        "random_element",
        elements=[choice.value for choice in TokenAcesso.TipoUsuario],
    )
    estado = factory.Faker(
        "random_element",
        elements=[choice.value for choice in TokenAcesso.Estado],
    )
    data_expiracao = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=30))

    @factory.post_generation
    def nucleos(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for nucleo in extracted:
                self.nucleos.add(nucleo)
        else:
            self.nucleos.add(NucleoFactory())
