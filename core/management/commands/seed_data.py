import random
from django.core.management.base import BaseCommand
from accounts.factories import UserFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
from empresas.factories import EmpresaFactory
from agenda.factories import EventoFactory
from tokens.factories import TokenAcessoFactory
from discussao.factories import CategoriaDiscussaoFactory, TopicoDiscussaoFactory
from feed.factories import PostFactory

class Command(BaseCommand):
    help = "Popula o banco de dados com dados de exemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Limpa o banco de dados antes de popular.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Limpando o banco de dados...")
            from django.core.management import call_command

            call_command("flush", interactive=False)

        self.stdout.write("Criando organizações...")
        organizacoes = OrganizacaoFactory.create_batch(2)

        for organizacao in organizacoes:
            self.stdout.write(f"Criando núcleos para {organizacao.nome}...")
            nucleos = NucleoFactory.create_batch(2, organizacao=organizacao)

            self.stdout.write(f"Criando usuários para {organizacao.nome}...")
            admins = UserFactory.create_batch(1, is_staff=True, organizacao=organizacao)
            gerentes = UserFactory.create_batch(2, organizacao=organizacao)
            clientes = UserFactory.create_batch(20, organizacao=organizacao, nucleos=nucleos)

            self.stdout.write(f"Criando empresas para {organizacao.nome}...")
            for cliente in clientes:
                EmpresaFactory.create_batch(random.randint(1, 2), usuario=cliente, organizacao=organizacao)

            self.stdout.write(f"Criando eventos para {organizacao.nome}...")
            EventoFactory.create_batch(6, organizacao=organizacao)

            self.stdout.write(f"Criando tokens de acesso para {organizacao.nome}...")
            TokenAcessoFactory.create_batch(5, organizacao=organizacao, usuario=random.choice(clientes))

            self.stdout.write(f"Criando categorias de discussão para {organizacao.nome}...")
            categorias = CategoriaDiscussaoFactory.create_batch(3, organizacao=organizacao)

            for categoria in categorias:
                self.stdout.write(f"Criando tópicos para a categoria {categoria.nome}...")
                TopicoDiscussaoFactory.create_batch(5, categoria=categoria, autor=random.choice(clientes + gerentes))

            self.stdout.write(f"Criando postagens no feed para {organizacao.nome}...")
            for cliente in clientes:
                PostFactory.create_batch(3, autor=cliente)

            self.stdout.write(f"Preenchendo campos opcionais para usuários de {organizacao.nome}...")
            for user in clientes + gerentes + admins:
                user.bio = "Bio gerada automaticamente."
                user.avatar = "https://via.placeholder.com/150"
                user.save()

        self.stdout.write(self.style.SUCCESS("Banco de dados populado com sucesso!"))
