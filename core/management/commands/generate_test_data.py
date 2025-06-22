from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from accounts.models import UserType
from organizacoes.models import Organizacao
from nucleos.models import Nucleo
from empresas.models import Empresa, Tag
from eventos.models import Evento
from django.utils import timezone
from faker import Faker
from datetime import timedelta
import itertools
import random
import csv
import io


class Command(BaseCommand):
    help = "Generate sample organizations, nuclei and users"

    NUCLEO_NOMES = ["CDL Mulher", "CDL Jovem"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["json", "csv"],
            default="json",
            help="Output format"
        )

    def handle(self, *args, **options):
        faker = Faker("pt_BR")
        User = get_user_model()

        # Limpa dados previamente gerados (exceto tipos e superusuários)
        User.objects.filter(is_superuser=False).delete()
        Empresa.objects.all().delete()
        Evento.objects.all().delete()
        Nucleo.objects.all().delete()
        Organizacao.objects.all().delete()
        Tag.objects.all().delete()

        # Tipos de usuario padrao
        tipos = ["admin", "manager", "client", "root"]
        for idx, desc in enumerate(tipos, start=1):
            UserType.objects.get_or_create(id=idx, defaults={"descricao": desc})

        # Organizacoes padrao
        org_data = [
            ("CDL Blumenau", "87.640.225/0001-55"),
            ("CDL Balneário Camboriú", "21.819.123/0001-65"),
        ]
        orgs = []
        for nome, cnpj in org_data:
            org, _ = Organizacao.objects.get_or_create(nome=nome, defaults={"cnpj": cnpj})
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

        def criar_usuario(tipo_desc):
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
                    "cpf": faker.cpf(),
                    "genero": genero,
                    "tipo": UserType.objects.get(descricao=tipo_desc),
                    "organizacao": random.choice(orgs),
                },
            )
            user.set_password("J0529*4351")
            user.save(update_fields=["password"])
            return user

        clientes = [criar_usuario("client") for _ in range(100)]
        gerentes = [criar_usuario("manager") for _ in range(10)]
        admins = [criar_usuario("admin") for _ in range(5)]

        # Atribui gerentes a núcleos de forma circular
        for org in orgs:
            nucleos = nucleos_by_org[org]
            gerentes_org = [g for g in gerentes if g.organizacao == org]
            if not gerentes_org:
                continue
            ger_cycle = itertools.cycle(gerentes_org)
            for nucleo in nucleos:
                nucleo.membros.add(next(ger_cycle))

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

        # Cria algumas tags e empresas vinculadas a clientes
        tags = []
        for _ in range(5):
            tag, _ = Tag.objects.get_or_create(nome=faker.unique.word())
            tags.append(tag)

        for _ in range(20):
            usuario = random.choice(clientes)
            empresa = Empresa.objects.create(
                usuario=usuario,
                cnpj=faker.cnpj(),
                nome=faker.company(),
                tipo=faker.bs().title(),
                municipio=faker.city(),
                estado=faker.estado_sigla(),
                descricao=faker.text(),
                contato=faker.phone_number(),
                palavras_chave=";".join(faker.words(nb=3)),
            )
            empresa.tags.add(*random.sample(tags, k=2))

        # Cria eventos para cada organização
        for org in orgs:
            for _ in range(5):
                evento = Evento.objects.create(
                    organizacao=org,
                    titulo=faker.catch_phrase(),
                    descricao=faker.text(),
                    data_hora=timezone.now()
                    + timedelta(days=random.randint(1, 30), hours=random.randint(0, 23)),
                    duracao=timedelta(hours=random.randint(1, 3)),
                    link_inscricao=faker.url(),
                    briefing=faker.text(),
                )
                inscritos = random.sample(clientes, k=5)
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
                writer.writerow([
                    user.username,
                    user.email,
                    user.tipo.descricao,
                    user.organizacao.nome,
                ])

