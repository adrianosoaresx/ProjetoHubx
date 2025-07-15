import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from organizacoes.factories import OrganizacaoFactory

# Criar organizações
print("Populando tabela Organizacao...")
for _ in range(10):
    OrganizacaoFactory.create()
print("População concluída com sucesso!")
