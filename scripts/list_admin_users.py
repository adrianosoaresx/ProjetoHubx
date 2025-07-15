import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from accounts.models import User

# Listar usuários admin
print("Listando usuários admin:")
admin_users = User.objects.filter(tipo__descricao="admin")
for user in admin_users:
    print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Organização: {user.organizacao.nome}")
