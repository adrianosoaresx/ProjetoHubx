from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from organizacoes.models import Organizacao
from nucleos.models import Nucleo
from empresas.models import Empresa
from feed.models import Post

# O app 'discussao' foi removido; tornar import opcional
try:  # pragma: no cover
    from discussao.models import CategoriaDiscussao, TopicoDiscussao  # type: ignore

    DISCUSSAO_INSTALLED = True
except Exception:  # ImportError
    CategoriaDiscussao = None  # type: ignore
    TopicoDiscussao = None  # type: ignore
    DISCUSSAO_INSTALLED = False

User = get_user_model()


class Command(BaseCommand):
    help = "Popula o banco de dados com dados fictícios e realistas."

    def handle(self, *args, **kwargs):
        self.stdout.write("Criando organizações...")
        org_a = Organizacao.objects.create(nome="Organizacao A", cnpj="00.000.000/0001-91")
        org_b = Organizacao.objects.create(nome="Organizacao B", cnpj="00.000.000/0002-72")

        for org in [org_a, org_b]:
            self.stdout.write(f"Populando dados para {org.nome}...")

            admin = User.objects.create_user(
                email=f"admin@{org.nome.lower()}.com", password="admin123", is_staff=True, organizacao=org
            )

            coordenador = User.objects.create_user(
                email=f"coordenador@{org.nome.lower()}.com",
                password="coordenador123",
                is_associado=True,
                is_coordenador=True,
                organizacao=org,
            )

            nucleo = Nucleo.objects.create(nome="Núcleo 1", organizacao=org)
            coordenador.nucleo = nucleo
            coordenador.save()

            for i in range(2):
                User.objects.create_user(
                    email=f"nucleado{i + 1}@{org.nome.lower()}.com",
                    password="nucleado123",
                    is_associado=True,
                    nucleo=nucleo,
                    organizacao=org,
                )

            for i in range(2):
                User.objects.create_user(
                    email=f"associado{i + 1}@{org.nome.lower()}.com",
                    password="associado123",
                    is_associado=True,
                    organizacao=org,
                )

            for i in range(2):
                User.objects.create_user(
                    email=f"convidado{i + 1}@{org.nome.lower()}.com", password="convidado123", organizacao=org
                )

            for i in range(2):
                Empresa.objects.create(
                    nome=f"Empresa {i + 1} - {org.nome}", cnpj=f"00.000.000/000{i + 1}", organizacao=org
                )

            for i in range(3):
                Post.objects.create(autor=admin, conteudo=f"Postagem {i + 1} da {org.nome}", organizacao=org)

            if DISCUSSAO_INSTALLED:
                categoria = CategoriaDiscussao.objects.create(  # type: ignore[attr-defined]
                    nome="Categoria Geral", organizacao=org
                )

                for i in range(2):
                    TopicoDiscussao.objects.create(  # type: ignore[attr-defined]
                        categoria=categoria,
                        autor=admin,
                        titulo=f"Tópico {i + 1} da {org.nome}",
                        conteudo="Conteúdo do tópico",
                    )

        self.stdout.write(self.style.SUCCESS("Dados populados com sucesso!"))
