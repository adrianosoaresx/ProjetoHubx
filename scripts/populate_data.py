"""
Script para popular o banco de dados Django Hubx com dados de demonstração.

Este script utiliza o ORM do Django para criar um usuário root, dois
administradores, duas organizações com seus respectivos núcleos, usuários
associados, nucleados e convidados, eventos de demonstração e registros
financeiros. O saldo de cada centro de custo é calculado automaticamente
com base nos lançamentos de aportes externos e despesas.

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
from datetime import datetime, timedelta
from decimal import Decimal

import django


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
    from django.db.models import Case, DecimalField, F, Sum, Value, When
    from django.utils.text import slugify

    from agenda.models import Evento
    from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
    from nucleos.models import Nucleo, ParticipacaoNucleo
    from organizacoes.models import Organizacao

    # Garante que todas as operações de criação sejam atômicas
    User = get_user_model()
    with transaction.atomic():
        # Usuário root
        root, _ = User.objects.get_or_create(
            email="root@hubx.com.br",
            defaults={
                "username": "root",
                "first_name": "Root",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
                "user_type": "root",
            },
        )
        # Define senha padrão caso esteja vazia
        if not root.has_usable_password():
            root.set_password("password123")
            root.save()

        # Administradores
        admin_info = [
            ("admin1@hubx.com.br", "admin1", "Admin", "One"),
            ("admin2@hubx.com.br", "admin2", "Admin", "Two"),
        ]
        admins: list = []
        for email, username, first_name, last_name in admin_info:
            admin, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": True,
                    "is_superuser": False,
                    "user_type": "admin",
                },
            )
            if not admin.has_usable_password():
                admin.set_password("password123")
                admin.save()
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
        for org in organizacoes:
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

        # Centros de custo por organização
        centro_custo_por_org: dict = {}
        for org in organizacoes:
            cc, _ = CentroCusto.objects.get_or_create(
                organizacao=org,
                nucleo=None,
                evento=None,
                defaults={
                    "nome": "Centro de Custo Principal",
                    "tipo": "organizacao",
                    "descricao": "",
                    "saldo": Decimal("0"),
                },
            )
            centro_custo_por_org[org] = cc

        # Eventos de demonstração (3 por organização)
        for org, admin in zip(organizacoes, admins):
            nucleos = nucleos_por_org[org]
            for i in range(3):
                inicio = datetime.now() + timedelta(days=30 * (i + 1))
                fim = inicio + timedelta(hours=2)
                titulo = f"Evento {i + 1} - {org.nome}"
                Evento.objects.get_or_create(
                    titulo=titulo,
                    data_inicio=inicio,
                    organizacao=org,
                    defaults={
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
                        "orcamento": None,
                        "orcamento_estimado": None,
                        "valor_gasto": None,
                        "participantes_maximo": None,
                        "espera_habilitada": False,
                        "cronograma": "",
                        "informacoes_adicionais": "",
                        "contato_nome": "Contato",
                        "contato_email": f"contato@{slugify(org.nome)}.com",
                        "contato_whatsapp": "",
                    },
                )

        # Criação de usuários associados, nucleados e convidados
        for org in organizacoes:
            nucleos = nucleos_por_org[org]
            # 50 associados
            for i in range(50):
                email = f"assoc{i + 1}@{slugify(org.nome)}.com"
                username = f"assoc{i + 1}_{organizacoes.index(org) + 1}"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "first_name": "Associado",
                        "last_name": str(i + 1),
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
                ContaAssociado.objects.get_or_create(user=user)
            # 30 nucleados
            for i in range(30):
                nucleo = nucleos[i % len(nucleos)]
                email = f"nucleado{i + 1}@{slugify(org.nome)}.com"
                username = f"nucleado{i + 1}_{organizacoes.index(org) + 1}"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "first_name": "Nucleado",
                        "last_name": str(i + 1),
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
                ParticipacaoNucleo.objects.get_or_create(
                    user=user,
                    nucleo=nucleo,
                    defaults={"papel": "membro", "status": "ativo"},
                )
                ContaAssociado.objects.get_or_create(user=user)
            # 5 convidados
            for i in range(5):
                email = f"convidado{i + 1}@{slugify(org.nome)}.com"
                username = f"convidado{i + 1}_{organizacoes.index(org) + 1}"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "first_name": "Convidado",
                        "last_name": str(i + 1),
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

        # Registros financeiros (3 meses) e atualização de saldo
        for org in organizacoes:
            cc = centro_custo_por_org[org]
            for month_offset in range(3, 0, -1):
                date_ref = datetime.now() - timedelta(days=30 * month_offset)
                # Aporte externo (receita)
                LancamentoFinanceiro.objects.create(
                    centro_custo=cc,
                    tipo=LancamentoFinanceiro.Tipo.APORTE_EXTERNO,
                    valor=Decimal("5000.00"),
                    data_lancamento=date_ref,
                    data_vencimento=date_ref,
                    status=LancamentoFinanceiro.Status.PAGO,
                    origem=LancamentoFinanceiro.Origem.MANUAL,
                    descricao=f"Aporte externo referente ao mês {date_ref.strftime('%Y-%m')}",
                )
                # Despesa (saída)
                LancamentoFinanceiro.objects.create(
                    centro_custo=cc,
                    tipo=LancamentoFinanceiro.Tipo.DESPESA,
                    valor=Decimal("2000.00"),
                    data_lancamento=date_ref + timedelta(days=2),
                    data_vencimento=date_ref + timedelta(days=2),
                    status=LancamentoFinanceiro.Status.PAGO,
                    origem=LancamentoFinanceiro.Origem.MANUAL,
                    descricao=f"Despesa operacional referente ao mês {date_ref.strftime('%Y-%m')}",
                )
            # Calcula o saldo: receitas (aportes externos) menos despesas
            saldo = (
                LancamentoFinanceiro.objects.filter(centro_custo=cc)
                .aggregate(
                    saldo=Sum(
                        Case(
                            When(tipo=LancamentoFinanceiro.Tipo.APORTE_EXTERNO, then=F("valor")),
                            When(tipo=LancamentoFinanceiro.Tipo.DESPESA, then=F("valor") * -1),
                            default=Value(0),
                            output_field=DecimalField(),
                        )
                    )
                )
                .get("saldo")
                or Decimal("0")
            )
            if cc.saldo != saldo:
                cc.saldo = saldo
                cc.save(update_fields=["saldo"])

        print("Base de dados populada com sucesso!")


if __name__ == "__main__":
    setup_django()
    main()