import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from nucleos.models import Nucleo

# Listar núcleos
print("Listando núcleos:")
nucleos = Nucleo.objects.all()
for nucleo in nucleos:
    print(f"ID: {nucleo.id}, Nome: {nucleo.nome}, Organização: {nucleo.organizacao.nome}")
