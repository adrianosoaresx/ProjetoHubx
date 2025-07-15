import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from faker import Faker
from empresas.models import Tag, Empresa

# Criar tags e associá-las às empresas
print("Criando tags e associando às empresas...")
fake = Faker("pt_BR")
empresas = Empresa.objects.all()

# Criar 10 tags para produtos e serviços
for _ in range(5):
    Tag.objects.create(nome=fake.word().capitalize(), categoria=Tag.Categoria.PRODUTO)

for _ in range(5):
    Tag.objects.create(nome=fake.word().capitalize(), categoria=Tag.Categoria.SERVICO)

# Associar tags às empresas
for empresa in empresas:
    tags = Tag.objects.order_by('?')[:3]  # Selecionar 3 tags aleatórias
    empresa.tags.set(tags)

print("Tags criadas e associadas com sucesso!")
