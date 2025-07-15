import sys
from pathlib import Path

# Adicionar o diretório do projeto ao PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Listar todos os usuários
users = User.objects.all()

print("Usuários cadastrados:")
for user in users:
    print(f"Usuário: {user.username}, Email: {user.email}, Tipo: {getattr(user, 'tipo', 'N/A')}")

# Filtrar root e administradores
root_user = users.filter(username="root").first()
admin_users = users.filter(tipo=getattr(User.Tipo, 'ADMIN', None))

if root_user:
    print("\nUsuário Root:")
    print(f"Usuário: {root_user.username}, Email: {root_user.email}")

if admin_users.exists():
    print("\nAdministradores:")
    for admin in admin_users:
        print(f"Usuário: {admin.username}, Email: {admin.email}")
