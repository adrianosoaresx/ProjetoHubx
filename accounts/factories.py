import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from nucleos.factories import NucleoFactory

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name", locale="pt_BR")
    email = factory.Faker("email", locale="pt_BR")
    contato = factory.Faker("name", locale="pt_BR")
    is_active = True

    @factory.post_generation
    def nucleo_obj(self, create, extracted, **kwargs):
        if not create:
            return

        self.nucleo = extracted or NucleoFactory()
        self.save()
