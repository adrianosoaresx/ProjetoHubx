import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from faker import Faker

# Criar núcleos para cada organização
print("Criando 10 núcleos para cada organização...")
fake = Faker("pt_BR")
organizacoes = Organizacao.objects.all()

for organizacao in organizacoes:
    for i in range(10):
        Nucleo.objects.create(
            organizacao=organizacao,
            nome=fake.company(),
            descricao=fake.catch_phrase(),
        )

print("Núcleos criados com sucesso!")
