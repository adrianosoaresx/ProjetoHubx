import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from faker import Faker
from nucleos.models import Nucleo
from produtos.models import Produto, Servico
from organizacoes.models import Organizacao
from accounts.models import User

# Criar dados de produtos e serviços
print("Criando produtos e serviços para cada organização...")
fake = Faker("pt_BR")
organizacoes = Organizacao.objects.all()

for organizacao in organizacoes:
    # Criar 5 produtos para cada organização
    for _ in range(5):
        Produto.objects.create(
            nome=fake.word().capitalize(),
            descricao=fake.sentence(),
            preco=fake.random_number(digits=5, fix_len=True) / 100,
            organizacao=organizacao
        )

    # Criar 3 serviços para cada organização
    for _ in range(3):
        Servico.objects.create(
            nome=fake.word().capitalize(),
            descricao=fake.sentence(),
            preco=fake.random_number(digits=5, fix_len=True) / 100,
            organizacao=organizacao
        )

print("Produtos e serviços criados com sucesso!")

# Criar organizações para cada usuário cliente e gerente
print("Criando organizações para cada usuário cliente e gerente...")
usuarios = User.objects.filter(tipo__descricao__in=["cliente", "gerente"])

for usuario in usuarios:
    Organizacao.objects.create(
        nome=f"Organizacao_{usuario.username}",
        descricao=f"Organização associada ao usuário {usuario.username}",
        cnpj=fake.bothify(text="##.###.###/####-##"),
        usuario=usuario
    )

print("Organizações criadas com sucesso!")
