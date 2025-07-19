import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from accounts.factories import UserFactory
from agenda.factories import EventoFactory
from agenda.models import FeedbackNota, InscricaoEvento, ParceriaEvento
from chat.models import ChatConversation, ChatMessage, ChatParticipant
from discussao.factories import CategoriaDiscussaoFactory, TopicoDiscussaoFactory
from empresas.factories import EmpresaFactory
from empresas.models import Empresa
from feed.factories import PostFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory
from tokens.factories import TokenAcessoFactory


class Command(BaseCommand):
    help = "Popula o banco de dados com dados de exemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Limpa o banco de dados antes de popular.",
        )

    def handle(self, *args, **options):
        faker = Faker("pt_BR")
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
            clientes = UserFactory.create_batch(20, organizacao=organizacao)

            for cliente in clientes:
                cliente.nucleo = random.choice(nucleos)
                cliente.save()

            self.stdout.write(f"Criando empresas para {organizacao.nome}...")
            for cliente in clientes:
                EmpresaFactory.create_batch(random.randint(1, 2), usuario=cliente, organizacao=organizacao)

            self.stdout.write(f"Criando eventos para {organizacao.nome}...")
            eventos = EventoFactory.create_batch(6, organizacao=organizacao)

            for evento in eventos:
                inscritos = random.sample(clientes, k=5)
                for inscrito in inscritos:
                    InscricaoEvento.objects.create(
                        user=inscrito,
                        evento=evento,
                        status=random.choice(["pendente", "confirmada", "cancelada"]),
                        presente=random.choice([True, False]),
                    )

                for inscrito in inscritos[:3]:
                    FeedbackNota.objects.create(
                        evento=evento,
                        usuario=inscrito,
                        nota=random.randint(1, 5),
                        comentario=faker.sentence(),
                    )

                empresas_org = list(Empresa.objects.filter(organizacao=organizacao))
                for empresa in random.sample(empresas_org, k=min(2, len(empresas_org))):
                    ParceriaEvento.objects.create(
                        evento=evento,
                        empresa=empresa,
                        nucleo=random.choice(nucleos),
                        whatsapp_contato=faker.msisdn(),
                        tipo_parceria=random.choice(
                            [
                                "patrocinio",
                                "mentoria",
                                "mantenedor",
                                "outro",
                            ]
                        ),
                        data_inicio=timezone.now().date(),
                        data_fim=timezone.now().date() + timezone.timedelta(days=30),
                        descricao=faker.sentence(),
                    )

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

            self.stdout.write(f"Criando chats para {organizacao.nome}...")
            conv = ChatConversation.objects.create(
                slug=f"chat-{organizacao.id}",
                tipo_conversa="organizacao",
                organizacao=organizacao,
                titulo=f"Chat {organizacao.nome}",
            )
            participantes = random.sample(clientes + gerentes + admins, k=5)
            for usuario in participantes:
                ChatParticipant.objects.create(conversation=conv, user=usuario)
            for _ in range(10):
                ChatMessage.objects.create(
                    conversation=conv,
                    sender=random.choice(participantes),
                    conteudo=faker.sentence(),
                )

            self.stdout.write(f"Preenchendo campos opcionais para usuários de {organizacao.nome}...")
            for user in clientes + gerentes + admins:
                user.bio = "Bio gerada automaticamente."
                user.avatar = "https://via.placeholder.com/150"
                user.save()

        self.stdout.write(self.style.SUCCESS("Banco de dados populado com sucesso!"))
