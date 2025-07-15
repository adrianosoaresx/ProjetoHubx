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
from forum.models import Categoria, Topico, Resposta
from organizacoes.models import Organizacao

# Criar dados para o app forum
print("Criando dados para o app forum...")
fake = Faker("pt_BR")
organizacoes = Organizacao.objects.all()
usuarios = User.objects.all()

for organizacao in organizacoes:
    # Criar 3 categorias para cada organização
    for _ in range(3):
        categoria = Categoria.objects.create(
            nome=fake.word().capitalize(),
            descricao=fake.sentence(),
            organizacao=organizacao
        )

        # Criar 5 tópicos para cada categoria
        for _ in range(5):
            autor = fake.random_element(elements=usuarios)
            topico = Topico.objects.create(
                categoria=categoria,
                autor=autor,
                titulo=fake.sentence(),
                conteudo=fake.paragraph(),
                organizacao=organizacao
            )

            # Criar 3 respostas para cada tópico
            for _ in range(3):
                autor_resposta = fake.random_element(elements=usuarios)
                Resposta.objects.create(
                    topico=topico,
                    autor=autor_resposta,
                    conteudo=fake.paragraph()
                )

print("Dados do app forum criados com sucesso!")
