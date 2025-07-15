import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from accounts.models import UserType

# Populando tipos de usuário
print("Populando tabela UserType...")
user_types = [
    {"id": 1, "descricao": "root"},
    {"id": 2, "descricao": "admin"},
    {"id": 3, "descricao": "gerente"},
    {"id": 4, "descricao": "cliente"},
]

for user_type in user_types:
    UserType.objects.get_or_create(id=user_type["id"], defaults={"descricao": user_type["descricao"]})

print("População concluída com sucesso!")
