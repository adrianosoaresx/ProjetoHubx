import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from faker import Faker
from accounts.models import User
from feed.models import Post
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

# Criar dados para o app feed
print("Criando dados para o app feed...")
fake = Faker("pt_BR")
organizacoes = Organizacao.objects.all()
usuarios = User.objects.all()
nucleos = Nucleo.objects.all()

for organizacao in organizacoes:
    # Criar 10 postagens públicas para cada organização
    for _ in range(10):
        autor = fake.random_element(elements=usuarios)
        Post.objects.create(
            autor=autor,
            conteudo=fake.paragraph(),
            tipo_feed="global",
            organizacao=organizacao,
        )

    # Criar 5 postagens de núcleo para cada organização
    for _ in range(5):
        autor = fake.random_element(elements=usuarios)
        nucleo = fake.random_element(elements=nucleos)
        Post.objects.create(
            autor=autor,
            conteudo=fake.paragraph(),
            tipo_feed="nucleo",
            nucleo=nucleo,
            organizacao=organizacao,
        )

print("Dados do app feed criados com sucesso!")
