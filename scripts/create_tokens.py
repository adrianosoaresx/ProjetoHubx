import os
import sys
import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
django.setup()

from faker import Faker
from accounts.models import User
from tokens.models import TokenAcesso
from organizacoes.models import Organizacao
from datetime import timedelta
from django.utils.timezone import now

# Criar tokens vinculados aos usuários
print("Criando tokens vinculados aos usuários...")
fake = Faker("pt_BR")
usuarios = User.objects.all()
organizacao_padrao = Organizacao.objects.first()  # Organização padrão para associação

for usuario in usuarios:
    TokenAcesso.objects.create(
        codigo=fake.uuid4(),
        tipo_destino=fake.random_element(elements=["admin", "gerente", "cliente"]),
        estado=TokenAcesso.Estado.NAO_USADO,
        data_expiracao=now() + timedelta(days=30),
        gerado_por=usuario,
        usuario=usuario,
        organizacao=organizacao_padrao
    )

print("Tokens criados com sucesso!")
