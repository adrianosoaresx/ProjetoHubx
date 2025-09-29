"""
Script para popular o banco de dados Django Hubx com dados de demonstração.

Este script utiliza o ORM do Django para criar um usuário root, dois
administradores, duas organizações com seus respectivos núcleos, usuários
associados, nucleados e convidados, além de eventos de demonstração.

Para executar este script, basta rodá‑lo com um interpretador Python no
ambiente virtual do projeto. Ele espera que as configurações do Django
estejam acessíveis via variável de ambiente ``DJANGO_SETTINGS_MODULE`` e
adiciona o diretório raiz do projeto ao ``sys.path`` para permitir a
importação dos módulos de aplicativo. O script é idempotente: se rodado
múltiplas vezes, utilizará ``get_or_create`` para evitar duplicidade.
"""

from __future__ import annotations

import os
import sys
import pathlib
from datetime import timedelta
from decimal import Decimal

import django
from django.utils import timezone


def setup_django() -> None:
    """Configura o ambiente Django para uso do ORM no script standalone."""
    # Determina o diretório raiz do projeto (onde fica manage.py)
    base_dir = pathlib.Path(__file__).resolve().parents[1]
    if str(base_dir) not in sys.path:
        sys.path.append(str(base_dir))
    # Define o módulo de configurações do Django se não estiver definido
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()


def main() -> None:
    """Popula o banco de dados com dados iniciais usando o ORM do Django."""
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils.text import slugify

    from eventos.models import Evento
    from nucleos.models import Nucleo, ParticipacaoNucleo
    from organizacoes.models import Organizacao
    from faker import Faker

    fake = Faker("pt_BR")

    # Garante que todas as operações de criação sejam atômicas
    User = get_user_model()
    with transaction.atomic():
        # Usuário root
        root, _ = User.objects.get_or_create(
            email="root@hubx.com.br",
            defaults={
                "username": "root",
                "contato": "Root User",
                "is_staff": True,
                "is_superuser": True,
                "user_type": "root",
            },
        )
        # Define a senha padrão sempre para garantir contas válidas
        root.set_password("password123")
        root.save(update_fields=["password"])

        # Administradores
        admin_info = [
            ("admin1@hubx.com.br", "admin1", "Admin One"),
            ("admin2@hubx.com.br", "admin2", "Admin Two"),
        ]
        admins: list = []
        for email, username, contato in admin_info:
            admin, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "contato": contato,
                    "is_staff": True,
                    "is_superuser": False,
                    "user_type": "admin",
                },
            )
            admin.set_password("password123")
            admin.save(update_fields=["password"])
            admins.append(admin)

        # Organizações e ligação com administradores
        organizacoes_data = [
            ("CDL FLORIANOPOLIS", "Florianópolis", "SC", "00.000.000/0001-91", admins[0]),
            ("CDL BLUMENAU", "Blumenau", "SC", "00.000.000/0002-72", admins[1]),
        ]
        organizacoes: list = []
        for nome, cidade, estado, cnpj, admin in organizacoes_data:
            slug = slugify(nome)
            org, _ = Organizacao.objects.get_or_create(
                cnpj=cnpj,
                defaults={
                    "nome": nome,
                    "cidade": cidade,
                    "estado": estado,
                    "slug": slug,
                    "tipo": "ong",
                    "created_by": admin,
                },
            )
            # Vincula o administrador à organização
            if admin.organizacao != org:
                admin.organizacao = org
                admin.save(update_fields=["organizacao"])
            organizacoes.append(org)

        # Núcleos por organização
        nucleos_por_org: dict = {}
        for org_idx, org in enumerate(organizacoes, start=1):
            nucleos: list = []
            for nome_nucleo in ["NUCLEO DA MULHER", "NUCLEO DE TECNOLOGIA"]:
                slug = slugify(nome_nucleo)
                nucleo, _ = Nucleo.objects.get_or_create(
                    organizacao=org,
                    slug=slug,
                    defaults={
                        "nome": nome_nucleo,
                        "descricao": "",
                        "ativo": True,
                        "mensalidade": Decimal("30.00"),
                    },
                )
                nucleos.append(nucleo)
            nucleos_por_org[org] = nucleos

        # Eventos de demonstração (3 por organização)
        for org, admin in zip(organizacoes, admins):
            nucleos = nucleos_por_org[org]
            for i in range(3):
                inicio = timezone.now() + timedelta(days=30 * (i + 1))
                fim = inicio + timedelta(hours=2)
                titulo = f"Evento {i + 1} - {org.nome}"
                slug = slugify(titulo)
                Evento.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "titulo": titulo,
                        "data_inicio": inicio,
                        "organizacao": org,
                        "descricao": "Evento de demonstração gerado pelo script de dados.",
                        "data_fim": fim,
                        "local": "Auditório",
                        "cidade": org.cidade,
                        "estado": org.estado,
                        "cep": "88000-000" if org == organizacoes[0] else "89000-000",
                        "coordenador": admin,
                        "nucleo": nucleos[i % len(nucleos)],
                        "status": 0,
                        "publico_alvo": 0,
                        "numero_convidados": 5,
                        "numero_presentes": 0,
                        "valor_ingresso": None,
                        "orcamento_estimado": None,
                        "valor_gasto": None,
                        "participantes_maximo": None,
                        "cronograma": "",
                        "informacoes_adicionais": "",
                        "briefing": "",
                        "parcerias": "",
                        "contato_nome": "Contato",
                        "contato_email": f"contato@{slugify(org.nome)}.com",
                        "contato_whatsapp": "",
                    },
                )
                print(f"Criados {i + 1}/3 eventos para {org.nome}")

        # Criação de usuários associados, nucleados e convidados
        for org_idx, org in enumerate(organizacoes, start=1):
            nucleos = nucleos_por_org[org]
            # 50 associados
            for i in range(50):
                email = f"assoc{i + 1}@{slugify(org.nome)}.com"
                username = f"assoc{i + 1}_{org_idx}"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "contato": f"Associado {i + 1}",
                        "is_staff": False,
                        "is_superuser": False,
                        "user_type": "associado",
                        "is_associado": True,
                        "is_coordenador": False,
                        "organizacao": org,
                        "cidade": org.cidade,
                        "estado": org.estado,
                    },
                )
                if created:
                    user.set_password("password123")
                    user.save()
                elif user.organizacao != org or user.organizacao is None:
                    user.organizacao = org
                    user.save(update_fields=["organizacao"])
                if (i + 1) % 10 == 0:
                    print(f"Criados {i + 1}/50 associados para {org.nome}")
            # 30 nucleados
            for i in range(30):
                nucleo = nucleos[i % len(nucleos)]
                email = f"nucleado{i + 1}@{slugify(org.nome)}.com"
                username = f"nucleado{i + 1}_{org_idx}"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "contato": f"Nucleado {i + 1}",
                        "is_staff": False,
                        "is_superuser": False,
                        "user_type": "nucleado",
                        "is_associado": True,
                        "is_coordenador": False,
                        "organizacao": org,
                        "nucleo": nucleo,
                        "cidade": org.cidade,
                        "estado": org.estado,
                    },
                )
                if created:
                    user.set_password("password123")
                    user.save()
                else:
                    updated_fields = []
                    if user.organizacao != org or user.organizacao is None:
                        user.organizacao = org
                        updated_fields.append("organizacao")
                    if user.nucleo != nucleo:
                        user.nucleo = nucleo
                        updated_fields.append("nucleo")
                    if updated_fields:
                        user.save(update_fields=updated_fields)
                ParticipacaoNucleo.objects.get_or_create(
                    user=user,
                    nucleo=nucleo,
                    defaults={"papel": "membro", "status": "ativo"},
                )
                if (i + 1) % 10 == 0:
                    print(f"Criados {i + 1}/30 nucleados para {org.nome}")
            # 5 convidados
            for i in range(5):
                email = f"convidado{i + 1}@{slugify(org.nome)}.com"
                username = f"convidado{i + 1}_{org_idx}"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "contato": f"Convidado {i + 1}",
                        "is_staff": False,
                        "is_superuser": False,
                        "user_type": "convidado",
                        "is_associado": False,
                        "is_coordenador": False,
                        "organizacao": org,
                        "cidade": org.cidade,
                        "estado": org.estado,
                    },
                )
                if created:
                    user.set_password("password123")
                    user.save()
                elif user.organizacao != org or user.organizacao is None:
                    user.organizacao = org
                    user.save(update_fields=["organizacao"])
                print(f"Criados {i + 1}/5 convidados para {org.nome}")

        print("Base de dados populada com sucesso!")


if __name__ == "__main__":
    setup_django()
    main()
