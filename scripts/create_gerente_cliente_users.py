import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from accounts.models import User, UserType
from nucleos.models import Nucleo
from faker import Faker

# Criar usuários gerente e cliente
print("Criando usuários gerente e cliente para cada núcleo...")
fake = Faker("pt_BR")
gerente_type = UserType.objects.get(descricao="gerente")
cliente_type = UserType.objects.get(descricao="cliente")
nucleos = Nucleo.objects.all()

for nucleo in nucleos:
    # Criar um gerente para o núcleo
    User.objects.create_user(
        username=f"gerente_{nucleo.id}",
        email=f"gerente_{nucleo.id}@hubx.com",
        password="1234Hubx!",
        tipo=gerente_type,
        nucleo=nucleo
    )

    # Criar 5 clientes para o núcleo
    for i in range(5):
        User.objects.create_user(
            username=f"cliente_{nucleo.id}_{i}",
            email=f"cliente_{nucleo.id}_{i}@hubx.com",
            password="1234Hubx!",
            tipo=cliente_type,
            nucleo=nucleo
        )

print("Usuários gerente e cliente criados com sucesso!")
