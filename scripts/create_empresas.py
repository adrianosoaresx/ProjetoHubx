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
from empresas.models import Empresa
from organizacoes.models import Organizacao

# Criar empresas para cada usuário cliente e gerente
print("Criando empresas para cada usuário cliente e gerente...")
fake = Faker("pt_BR")
usuarios = User.objects.filter(tipo__descricao__in=["cliente", "gerente"])
organizacao_padrao = Organizacao.objects.first()  # Organização padrão para associação

for usuario in usuarios:
    Empresa.objects.create(
        usuario=usuario,
        cnpj=fake.bothify(text="##.###.###/####-##"),
        nome=f"Empresa_{usuario.username}",
        tipo=fake.random_element(elements=("Comércio", "Serviços", "Indústria")),
        municipio=fake.city(),
        estado=fake.state_abbr(),
        descricao=fake.catch_phrase(),
        organizacao=organizacao_padrao
    )

print("Empresas criadas com sucesso!")
