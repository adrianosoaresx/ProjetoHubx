import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from feed.models import Post


class PostFactory(DjangoModelFactory):
    class Meta:
        model = Post

    conteudo = factory.Faker("text", locale="pt_BR")
    autor = factory.SubFactory(UserFactory)
