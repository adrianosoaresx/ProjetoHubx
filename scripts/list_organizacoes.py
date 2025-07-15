import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from organizacoes.models import Organizacao

# Listar organizações
print("Listando organizações populadas:")
organizacoes = Organizacao.objects.all()
for organizacao in organizacoes:
    print(f"ID: {organizacao.id}, Nome: {organizacao.nome}, CNPJ: {organizacao.cnpj}")
