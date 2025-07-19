import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from feed.models import Post


class PostFactory(DjangoModelFactory):
    class Meta:
        model = Post

    conteudo = factory.Faker("text", locale="pt_BR")
    autor = factory.SubFactory(UserFactory)
    organizacao = factory.SelfAttribute("autor.organizacao")
    tipo_feed = factory.Faker("random_element", elements=[choice[0] for choice in Post.TIPO_FEED_CHOICES])
