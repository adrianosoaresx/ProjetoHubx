import csv
import io
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from accounts.models import UserType
from agenda.models import Evento
from empresas.models import Empresa, Tag
from nucleos.models import Nucleo
from organizacoes.models import Organizacao


class Command(BaseCommand):
    help = "Generate sample organizations, nuclei, users, tags, companies and events"

    NUCLEO_NOMES = ["CDL Mulher", "CDL Jovem"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--format", choices=["json", "csv"], default="json", help="Output format"
        )

    def handle(self, *args, **options):
        faker = Faker("pt_BR")
        User = get_user_model()

        root_user, _ = User.objects.get_or_create(
            username="root",
            defaults={
                "first_name": "root",
                "is_superuser": True,
                "is_staff": True,
                "user_type": UserType.ROOT,
            },
        )

        # Limpa dados previamente gerados (exceto tipos e superusuários)
        User.objects.filter(is_superuser=False).delete()
        Empresa.objects.all().delete()
        Evento.objects.all().delete()
        Nucleo.objects.all().delete()
        Organizacao.objects.all().delete()
        Tag.objects.all().delete()

        tipos = [UserType.ADMIN, UserType.GERENTE, UserType.CLIENTE]

        # Organizacoes padrao
        org_data = [
            ("CDL Blumenau", "87.640.225/0001-55"),
            ("CDL Balneário Camburiú", "21.819.123/0001-65"),
        ]
        orgs = []
        for nome, cnpj in org_data:
            org, _ = Organizacao.objects.get_or_create(
                nome=nome, defaults={"cnpj": cnpj}
            )
            orgs.append(org)

        nucleos_by_org = {}
        for org in orgs:
            nomes = self.NUCLEO_NOMES[:]
            while len(nomes) < 10:
                nomes.append(faker.bs().title())
            random.shuffle(nomes)
            nucleos = []
            for nome in nomes:
                nucleo, _ = Nucleo.objects.get_or_create(organizacao=org, nome=nome)
                nucleos.append(nucleo)
            nucleos_by_org[org] = nucleos

        def criar_usuario(tipo_enum: UserType):
            primeiro = faker.first_name()
            ultimo = faker.last_name()
            username = faker.unique.user_name()
            genero = random.choice(["M", "F"])
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": primeiro,
                    "last_name": ultimo,
                    "email": faker.unique.email(),
                    "cpf": faker.unique.cpf(),
                    "genero": genero,
                    "user_type": tipo_enum,
                    "organizacao": random.choice(orgs),
                },
            )
            return user

        clientes = [criar_usuario(UserType.CLIENTE) for _ in range(100)]
        gerentes = [criar_usuario(UserType.GERENTE) for _ in range(10)]
        admins = [criar_usuario(UserType.ADMIN) for _ in range(5)]

        # Atribui gerentes a nucleos
        for org in orgs:
            nucleos = nucleos_by_org[org]
            gerentes_org = [g for g in gerentes if g.organizacao == org]
            for nucleo, gerente in zip(nucleos, gerentes_org):
                nucleo.membros.add(gerente)

        cdl_mulher_map = {
            org.id: Nucleo.objects.get(organizacao=org, nome="CDL Mulher")
            for org in orgs
        }

        for cliente in clientes:
            if cliente.genero == "F":
                nucleo = cdl_mulher_map[cliente.organizacao_id]
            else:
                nucleo = random.choice(nucleos_by_org[cliente.organizacao])
            nucleo.membros.add(cliente)

        for admin in admins:
            nucleo = random.choice(nucleos_by_org[admin.organizacao])
            nucleo.membros.add(admin)

        # Cria tags de produtos e serviços
        tags_prod = []
        for _ in range(5):
            tag, _ = Tag.objects.get_or_create(
                nome=faker.unique.word(),
                defaults={"categoria": Tag.Categoria.PRODUTO},
            )
            tags_prod.append(tag)

        tags_serv = []
        for _ in range(5):
            tag, _ = Tag.objects.get_or_create(
                nome=faker.unique.word(),
                defaults={"categoria": Tag.Categoria.SERVICO},
            )
            tags_serv.append(tag)

        # Distribui usuários em grupos de empresa (1 ou 2)
        random.shuffle(clientes)
        metade = len(clientes) // 2
        usuarios_uma_empresa = clientes[:metade]
        usuarios_duas_empresas = clientes[metade:]

        # Distribui usuários em grupos de serviço/produto
        usuarios_servico = set(random.sample(clientes, metade))
        restantes = [c for c in clientes if c not in usuarios_servico]
        metade_restante = len(restantes) // 2
        usuarios_um_produto = restantes[:metade_restante]
        usuarios_dois_produtos = restantes[metade_restante:]

        def criar_empresa(usuario):
            empresa = Empresa.objects.create(
                usuario=usuario,
                cnpj=faker.unique.cnpj(),
                nome=faker.company(),
                tipo=faker.bs().title(),
                municipio=faker.city(),
                estado=faker.estado_sigla(),
                descricao=faker.text(),
                contato=faker.phone_number(),
                palavras_chave=";".join(faker.words(nb=3)),
            )

            if usuario in usuarios_servico:
                empresa.tags.add(random.choice(tags_serv))
            elif usuario in usuarios_um_produto:
                empresa.tags.add(random.choice(tags_prod))
            else:
                empresa.tags.add(*random.sample(tags_prod, k=2))

            return empresa

        for usuario in usuarios_uma_empresa:
            criar_empresa(usuario)

        for usuario in usuarios_duas_empresas:
            criar_empresa(usuario)
            criar_empresa(usuario)

        # Criar empresas para admins e gerentes
        for user in User.objects.filter(tipo__descricao__in=["admin", "manager"]):
            Empresa.objects.create(
                cnpj=faker.cnpj(),
                nome=faker.company(),
                tipo=random.choice(["MEI", "LTDA", "EIRELI"]),
                municipio=faker.city(),
                estado=faker.state_abbr(),
                descricao=faker.text(),
                contato=faker.phone_number(),
                usuario=user,
                organizacao=user.organizacao,
            )

        # Relacionamentos de conexão e seguidores dentro da mesma organização
        todos_usuarios = clientes + gerentes + admins
        usuarios_por_org = {}
        for u in todos_usuarios:
            usuarios_por_org.setdefault(u.organizacao_id, []).append(u)

        for usuarios_org in usuarios_por_org.values():
            for usuario in usuarios_org:
                possiveis = [u for u in usuarios_org if u != usuario]
                if not possiveis:
                    continue

                num_conexoes = random.randint(0, min(5, len(possiveis)))
                usuario.connections.add(*random.sample(possiveis, num_conexoes))

                num_seguidos = random.randint(0, min(10, len(possiveis)))
                usuario.following.add(*random.sample(possiveis, num_seguidos))

        # Conecta todos os usuários ao superusuário "root"
        if root_user:
            root_user.connections.add(*todos_usuarios)
            for user in todos_usuarios:
                user.connections.add(root_user)

        # Conecta cada gerente a um admin da mesma organização
        admins_por_org = {}
        for admin in admins:
            admins_por_org.setdefault(admin.organizacao_id, []).append(admin)

        for gerente in gerentes:
            admins_org = admins_por_org.get(gerente.organizacao_id)
            if admins_org:
                gerente.connections.add(random.choice(admins_org))

        # Conecta cada cliente a um gerente da mesma organização
        gerentes_por_org = {}
        for gerente in gerentes:
            gerentes_por_org.setdefault(gerente.organizacao_id, []).append(gerente)

        for cliente in clientes:
            gerentes_org = gerentes_por_org.get(cliente.organizacao_id)
            if gerentes_org:
                cliente.connections.add(random.choice(gerentes_org))

        # Cria eventos para cada organização
        for org in orgs:
            for _ in range(5):
                evento = Evento.objects.create(
                    organizacao=org,
                    titulo=faker.catch_phrase(),
                    descricao=faker.text(),
                    data_hora=timezone.now()
                    + timedelta(
                        days=random.randint(1, 30), hours=random.randint(0, 23)
                    ),
                    duracao=timedelta(hours=random.randint(1, 3)),
                    link_inscricao=faker.url(),
                    briefing=faker.text(),
                )
                # Inscreve apenas clientes da mesma organização
                clientes_org = [c for c in clientes if c.organizacao == org]
                inscritos = random.sample(clientes_org, k=5)
                evento.inscritos.add(*inscritos)

        output_format = options["format"]
        if output_format == "json":
            buf = io.StringIO()
            call_command("dumpdata", indent=2, stdout=buf)
            self.stdout.write(buf.getvalue())
        else:
            writer = csv.writer(self.stdout)
            writer.writerow(["username", "email", "tipo", "organizacao"])
            for user in clientes + gerentes + admins:
                writer.writerow(
                    [
                        user.username,
                        user.email,
                        user.tipo.descricao,
                        user.organizacao.nome,  # Corrigido para usar 'organization'
                    ]
                )

        # Ajustar CSV writer para incluir organizacao
        if options["format"] == "csv":
            with io.StringIO() as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["cnpj", "nome", "tipo", "municipio", "estado", "organizacao"])
                for empresa in Empresa.objects.all():
                    writer.writerow([
                        empresa.cnpj,
                        empresa.nome,
                        empresa.tipo,
                        empresa.municipio,
                        empresa.estado,
                        empresa.organizacao.nome,
                    ])
                self.stdout.write(csvfile.getvalue())
