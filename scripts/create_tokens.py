import os
import sys

import django

# Adicionar o diretório do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar o ambiente do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")  # noqa: E402
django.setup()  # noqa: E402

from datetime import timedelta  # noqa: E402

from django.utils.timezone import now  # noqa: E402
from faker import Faker  # noqa: E402

from accounts.models import User  # noqa: E402
from organizacoes.models import Organizacao  # noqa: E402
from tokens.models import TokenAcesso  # noqa: E402

# Criar tokens vinculados aos usuários
print("Criando tokens vinculados aos usuários...")
fake = Faker("pt_BR")
usuarios = User.objects.all()
organizacao_padrao = Organizacao.objects.first()  # Organização padrão para associação

for usuario in usuarios:
    TokenAcesso.objects.create(
        codigo=fake.uuid4(),
        tipo_destino=fake.random_element(elements=[choice.value for choice in TokenAcesso.TipoUsuario]),
        estado=TokenAcesso.Estado.NOVO,
        data_expiracao=now() + timedelta(days=30),
        gerado_por=usuario,
        usuario=usuario,
        organizacao=organizacao_padrao,
    )

print("Tokens criados com sucesso!")
