import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from accounts.models import User, UserType

# Criar usuário root
print("Criando usuário root...")
root_type = UserType.objects.get(descricao="root")
User.objects.create_superuser(
    username="root",
    email="root@hubx.com",
    password="1234Hubx!",
    tipo=root_type
)
print("Usuário root criado com sucesso!")
