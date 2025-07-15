import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from tokens.models import TokenAcesso

# Atualizar o estado dos tokens vinculados a usuários
print("Atualizando o estado dos tokens vinculados a usuários...")
tokens = TokenAcesso.objects.filter(usuario__isnull=False)

for token in tokens:
    token.estado = TokenAcesso.Estado.USADO
    token.save()

print("Estado dos tokens atualizado com sucesso!")
