import factory
from factory.django import DjangoModelFactory
from feed.models import Post
from accounts.factories import UserFactory

class PostFactory(DjangoModelFactory):
    class Meta:
        model = Post

    conteudo = factory.Faker("text", locale="pt_BR")
    autor = factory.SubFactory(UserFactory)
