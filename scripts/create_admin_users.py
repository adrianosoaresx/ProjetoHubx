import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from accounts.models import User, UserType
from organizacoes.models import Organizacao

# Criar usuários admin para cada organização
print("Criando usuários admin para cada organização...")
organizacoes = Organizacao.objects.all()

for organizacao in organizacoes:
    User.objects.create_user(
        username=f"admin_{organizacao.id}",
        email=f"admin_{organizacao.id}@hubx.com",
        password="1234Hubx!",
        user_type=UserType.ADMIN,
        organizacao=organizacao
    )

print("Usuários admin criados com sucesso!")
