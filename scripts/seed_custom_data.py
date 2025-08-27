#!/usr/bin/env python
"""Script to populate database with predefined demo data."""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from faker import Faker
from validate_docbr import CNPJ, CPF

# ---------------------------------------------------------------------------
# Configuração do ambiente Django
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from django.utils.text import slugify  # noqa: E402

from accounts.models import User, UserType  # noqa: E402
from configuracoes.models import ConfiguracaoConta  # noqa: E402
from organizacoes.models import Organizacao  # noqa: E402
from nucleos.models import Nucleo, ParticipacaoNucleo  # noqa: E402
from agenda.models import Evento  # noqa: E402
from financeiro.models import CentroCusto, LancamentoFinanceiro  # noqa: E402

fake = Faker("pt_BR")
cpf = CPF()
cnpj = CNPJ()


@transaction.atomic
def clear_data() -> None:
    """Remove data previously created for demo purposes."""
    LancamentoFinanceiro.objects.all().delete()
    CentroCusto.objects.all().delete()
    Evento.all_objects.all().delete(soft=False)
    ParticipacaoNucleo.objects.all().delete()
    Nucleo.all_objects.all().delete(soft=False)
    Organizacao.all_objects.all().delete(soft=False)
    User.objects.exclude(username="root").delete()


@transaction.atomic
def create_demo_data() -> None:
    clear_data()

    # Root user
    root, _ = User.objects.get_or_create(
        username="root",
        defaults={
            "email": "root@hubx.com.br",
            "is_staff": True,
            "is_superuser": True,
            "user_type": UserType.ROOT,
        },
    )
    if not root.password:
        root.set_password("1234Hubx!")
        root.save()
    ConfiguracaoConta.objects.get_or_create(user=root)

    org_infos = [
        ("CDL FLORIANOPOLIS", "admin1", "admin1@hubx.com.br"),
        ("CDL BLUMENAU", "admin2", "admin2@hubx.com.br"),
    ]

    for nome_org, admin_username, admin_email in org_infos:
        org = Organizacao.objects.create(
            nome=nome_org,
            cnpj=cnpj.generate(),
            descricao=fake.catch_phrase(),
            slug=slugify(nome_org)[:50],
        )

        admin = User.objects.create_user(
            username=admin_username,
            email=admin_email,
            password="1234Hubx!",
            user_type=UserType.ADMIN,
            organizacao=org,
            nome_completo=fake.name(),
            cpf=cpf.generate(),
        )
        ConfiguracaoConta.objects.create(user=admin)

        nucleos = []
        for nome_nucleo in ["NUCLEO DA MULHER", "NUCLEO DE TECNOLOGIA"]:
            nucleos.append(
                Nucleo.objects.create(
                    organizacao=org,
                    nome=nome_nucleo,
                    descricao=fake.sentence(),
                )
            )

        # Usuários associados
        for i in range(50):
            user = User.objects.create_user(
                username=f"assoc_{org.pk}_{i}",
                email=f"assoc_{org.pk}_{i}@example.com",
                password="1234Hubx!",
                user_type=UserType.ASSOCIADO,
                organizacao=org,
                is_associado=True,
                nome_completo=fake.name(),
                cpf=cpf.generate(),
            )
            ConfiguracaoConta.objects.create(user=user)

        # Usuários nucleados (distribuídos entre os núcleos)
        for i in range(30):
            nucleo = nucleos[i % len(nucleos)]
            user = User.objects.create_user(
                username=f"nucleado_{org.pk}_{i}",
                email=f"nucleado_{org.pk}_{i}@example.com",
                password="1234Hubx!",
                user_type=UserType.NUCLEADO,
                organizacao=org,
                nucleo=nucleo,
                is_associado=True,
                nome_completo=fake.name(),
                cpf=cpf.generate(),
            )
            ConfiguracaoConta.objects.create(user=user)
            ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, status="ativo")

        # Usuários convidados
        for i in range(5):
            user = User.objects.create_user(
                username=f"guest_{org.pk}_{i}",
                email=f"guest_{org.pk}_{i}@example.com",
                password="1234Hubx!",
                user_type=UserType.CONVIDADO,
                organizacao=org,
                nome_completo=fake.name(),
                cpf=cpf.generate(),
            )
            ConfiguracaoConta.objects.create(user=user)

        # Eventos (3 por organização)
        for i in range(3):
            start = timezone.now() + timedelta(days=i + 1)
            end = start + timedelta(hours=2)
            Evento.objects.create(
                titulo=f"Evento {i + 1} - {org.nome}",
                descricao=fake.paragraph(),
                data_inicio=start,
                data_fim=end,
                local=fake.street_address(),
                cidade=fake.city(),
                estado=fake.state_abbr(),
                cep=fake.postcode(),
                coordenador=admin,
                organizacao=org,
                nucleo=nucleos[i % len(nucleos)],
                status=0,
                publico_alvo=0,
                numero_convidados=50,
                numero_presentes=0,
                valor_ingresso=Decimal("0.00"),
                orcamento=Decimal("100.00"),
                cronograma=fake.text(max_nb_chars=100),
                informacoes_adicionais=fake.text(max_nb_chars=50),
                contato_nome=fake.name(),
                contato_email=fake.email(),
                contato_whatsapp=fake.msisdn(),
            )

        # Dados financeiros (3 meses)
        centro = CentroCusto.objects.create(
            nome=f"Centro {org.nome}",
            tipo=CentroCusto.Tipo.ORGANIZACAO,
            organizacao=org,
        )
        for i in range(3):
            dt = timezone.now() - timedelta(days=30 * i)
            LancamentoFinanceiro.objects.create(
                centro_custo=centro,
                originador=admin,
                tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
                valor=Decimal("1000.00"),
                data_lancamento=dt,
                data_vencimento=dt + timedelta(days=15),
                status=LancamentoFinanceiro.Status.PAGO,
                descricao=f"Mensalidade {dt.strftime('%B/%Y')} {org.nome}",
            )


if __name__ == "__main__":
    create_demo_data()
