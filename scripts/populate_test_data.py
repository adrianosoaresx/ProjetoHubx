#!/usr/bin/env python
"""Populate database with realistic test data for all domains."""
# ruff: noqa: E402

from __future__ import annotations

import os
import random
import sys
from decimal import Decimal

# ---------------------------------------------------------------------------
# Configure o ambiente Django corretamente
# Inclua o diretório raiz do projeto no sys.path e defina DJANGO_SETTINGS_MODULE
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Use "Hubx.settings" pois a pasta do projeto se chama "Hubx"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker
from validate_docbr import CNPJ, CPF

from accounts.models import UserType
from agenda.models import Evento, InscricaoEvento, ParceriaEvento
from chat.models import ChatConversation, ChatMessage, ChatParticipant
from configuracoes.models import ConfiguracaoConta
from discussao.models import CategoriaDiscussao, RespostaDiscussao, TopicoDiscussao
from empresas.models import Empresa
from feed.models import Post
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao
from tokens.models import TokenAcesso

User = get_user_model()

# Instâncias de Faker e geradores de CPF/CNPJ
fake = Faker("pt_BR")
cpf = CPF()
cnpj = CNPJ()


def clear_test_data() -> None:
    """Remove previously generated data keeping only the root user."""
    TokenAcesso.objects.all().delete()
    ChatMessage.objects.all().delete()
    ChatParticipant.objects.all().delete()
    ChatConversation.objects.all().delete()
    RespostaDiscussao.objects.all().delete()
    TopicoDiscussao.objects.all().delete()
    CategoriaDiscussao.objects.all().delete()
    Post.objects.all().delete()
    InscricaoEvento.objects.all().delete()
    Evento.objects.all().delete()
    Empresa.objects.all().delete()
    ConfiguracaoConta.objects.exclude(user__is_superuser=True).delete()
    User.objects.filter(is_superuser=False).delete()
    Nucleo.objects.all().delete()
    Organizacao.objects.all().delete()


def create_organizacoes(qtd: int = 3) -> list[Organizacao]:
    orgs = []
    for i in range(qtd):
        name = fake.company()
        orgs.append(
            Organizacao(
                nome=name,
                cnpj=cnpj.generate(),
                descricao=fake.catch_phrase(),
                slug=slugify(f"{name}-{i}")[:50],
            )
        )
    Organizacao.objects.bulk_create(orgs)
    return list(Organizacao.objects.order_by("-id")[:qtd])


def create_nucleos(orgs: list[Organizacao], qtd_por_org: int = 2) -> list[Nucleo]:
    nucleos: list[Nucleo] = []
    for org in orgs:
        for _ in range(qtd_por_org):
            nucleos.append(
                Nucleo(
                    organizacao=org,
                    nome=fake.bs().title(),
                    descricao=fake.sentence(),
                )
            )
    Nucleo.objects.bulk_create(nucleos)
    return list(Nucleo.objects.filter(organizacao__in=orgs))


def create_users(orgs: list[Organizacao], nucleos: list[Nucleo]) -> tuple[list[User], list[tuple[str, str, str]]]:
    users: list[User] = []
    credentials: list[tuple[str, str, str]] = []
    # Usuário root/superadmin
    root_user, _ = User.objects.get_or_create(
        username="root",
        defaults={
            "email": "root@hubx.com",
            "is_staff": True,
            "is_superuser": True,
            "user_type": UserType.ROOT,
        },
    )
    if not root_user.password:
        root_user.set_password("1234Hubx!")
        root_user.save()
    ConfiguracaoConta.objects.get_or_create(user=root_user)
    users.append(root_user)
    credentials.append(("root", "root@hubx.com", "1234Hubx!"))
    # Demais perfis por organização
    for org in orgs:
        # Admin
        admin = User.objects.create_user(
            username=f"admin_{org.pk}",
            email=f"admin_{org.pk}@example.com",
            password="1234Hubx!",
            user_type=UserType.ADMIN,
            organizacao=org,
            nome_completo=fake.name(),
            cpf=cpf.generate(),
        )
        ConfiguracaoConta.objects.create(user=admin)
        users.append(admin)
        credentials.append((admin.username, admin.email, "1234Hubx!"))

        # Coordenador
        nucleo_org = random.choice([n for n in nucleos if n.organizacao_id == org.id])
        coordenador = User.objects.create_user(
            username=f"coord_{org.pk}",
            email=f"coord_{org.pk}@example.com",
            password="1234Hubx!",
            user_type=UserType.COORDENADOR,
            organizacao=org,
            nucleo=nucleo_org,
            is_associado=True,
            is_coordenador=True,
            nome_completo=fake.name(),
            cpf=cpf.generate(),
        )
        ConfiguracaoConta.objects.create(user=coordenador)
        ParticipacaoNucleo.objects.create(
            user=coordenador,
            nucleo=nucleo_org,
            is_coordenador=True,
        )
        users.append(coordenador)
        credentials.append((coordenador.username, coordenador.email, "1234Hubx!"))

        # Nucleado
        nucleo_org2 = random.choice([n for n in nucleos if n.organizacao_id == org.id])
        nucleado = User.objects.create_user(
            username=f"nucleado_{org.pk}",
            email=f"nucleado_{org.pk}@example.com",
            password="1234Hubx!",
            user_type=UserType.NUCLEADO,
            organizacao=org,
            nucleo=nucleo_org2,
            is_associado=True,
            nome_completo=fake.name(),
            cpf=cpf.generate(),
        )
        ConfiguracaoConta.objects.create(user=nucleado)
        ParticipacaoNucleo.objects.create(user=nucleado, nucleo=nucleo_org2)
        users.append(nucleado)
        credentials.append((nucleado.username, nucleado.email, "1234Hubx!"))

        # Associado
        associado = User.objects.create_user(
            username=f"assoc_{org.pk}",
            email=f"assoc_{org.pk}@example.com",
            password="1234Hubx!",
            user_type=UserType.ASSOCIADO,
            organizacao=org,
            is_associado=True,
            nome_completo=fake.name(),
            cpf=cpf.generate(),
        )
        ConfiguracaoConta.objects.create(user=associado)
        users.append(associado)
        credentials.append((associado.username, associado.email, "1234Hubx!"))

        # Convidado
        convidado = User.objects.create_user(
            username=f"guest_{org.pk}",
            email=f"guest_{org.pk}@example.com",
            password="1234Hubx!",
            user_type=UserType.CONVIDADO,
            organizacao=org,
            nome_completo=fake.name(),
            cpf=cpf.generate(),
        )
        ConfiguracaoConta.objects.create(user=convidado)
        users.append(convidado)
        credentials.append((convidado.username, convidado.email, "1234Hubx!"))
    return users, credentials


def create_eventos(nucleos: list[Nucleo], coordenadores: list[User]) -> list[Evento]:
    eventos: list[Evento] = []
    for nucleo in nucleos:
        coord = random.choice(coordenadores)
        start = fake.future_datetime()
        eventos.append(
            Evento(
                titulo=fake.sentence(),
                descricao=fake.paragraph(),
                data_inicio=start,
                data_fim=start + timezone.timedelta(hours=2),
                endereco=fake.street_address(),
                cidade=fake.city(),
                estado=fake.state_abbr(),
                cep=fake.postcode(),
                coordenador=coord,
                organizacao=nucleo.organizacao,
                nucleo=nucleo,
                status=0,
                publico_alvo=0,
                numero_convidados=20,
                numero_presentes=0,
                valor_ingresso=Decimal("0.00"),
                orcamento=Decimal("100.00"),
                cronograma=fake.text(max_nb_chars=100),
                informacoes_adicionais=fake.text(max_nb_chars=50),
                contato_nome=fake.name(),
                contato_email=fake.email(),
                contato_whatsapp=fake.msisdn(),
            )
        )
    Evento.objects.bulk_create(eventos)
    return list(Evento.objects.filter(nucleo__in=nucleos))


def create_inscricoes(eventos: list[Evento], participantes: list[User]) -> list[InscricaoEvento]:
    inscricoes: list[InscricaoEvento] = []
    for evento in eventos:
        inscritos = random.sample(participantes, min(len(participantes), 3))
        for user in inscritos:
            inscricoes.append(
                InscricaoEvento(
                    user=user,
                    evento=evento,
                    status="confirmada",
                    presente=False,
                    valor_pago=Decimal("0.00"),
                    metodo_pagamento="gratuito",
                )
            )
    InscricaoEvento.objects.bulk_create(inscricoes)
    return inscricoes


def create_feed(orgs: list[Organizacao], autores: list[User]) -> list[Post]:
    posts: list[Post] = []
    for org in orgs:
        for _ in range(5):
            autor = random.choice(autores)
            posts.append(
                Post(
                    autor=autor,
                    organizacao=org,
                    tipo_feed="global",
                    conteudo=fake.text(max_nb_chars=200),
                )
            )
    Post.objects.bulk_create(posts)
    return posts


def create_chat(orgs: list[Organizacao], users: list[User]) -> tuple[list[ChatConversation], list[ChatMessage]]:
    conversations: list[ChatConversation] = []
    for org in orgs:
        conversations.append(
            ChatConversation(
                titulo=f"Chat {org.nome}",
                slug=slugify(f"chat-{org.pk}"),
                tipo_conversa="organizacao",
                organizacao=org,
            )
        )
    ChatConversation.objects.bulk_create(conversations)
    conversations = list(ChatConversation.objects.filter(organizacao__in=orgs))

    participants: list[ChatParticipant] = []
    messages: list[ChatMessage] = []
    for conv in conversations:
        conv_users = [u for u in users if u.organizacao_id == conv.organizacao_id][:3]
        for u in conv_users:
            participants.append(ChatParticipant(conversation=conv, user=u))
        for _ in range(5):
            sender = random.choice(conv_users)
            messages.append(
                ChatMessage(
                    conversation=conv,
                    organizacao=conv.organizacao,
                    sender=sender,
                    conteudo=fake.sentence(),
                )
            )
    ChatParticipant.objects.bulk_create(participants)
    ChatMessage.objects.bulk_create(messages)
    return conversations, messages


def create_discussao(
    orgs: list[Organizacao], autores: list[User]
) -> tuple[list[CategoriaDiscussao], list[TopicoDiscussao]]:
    categorias: list[CategoriaDiscussao] = []
    for org in orgs:
        categorias.append(
            CategoriaDiscussao(
                nome=fake.word(),
                slug=slugify(f"cat-{org.pk}"),
                descricao=fake.sentence(),
                organizacao=org,
            )
        )
    CategoriaDiscussao.objects.bulk_create(categorias)
    categorias = list(CategoriaDiscussao.objects.filter(organizacao__in=orgs))

    topicos: list[TopicoDiscussao] = []
    respostas: list[RespostaDiscussao] = []
    for cat in categorias:
        autor = random.choice(autores)
        topico = TopicoDiscussao(
            categoria=cat,
            titulo=fake.sentence(),
            slug=slugify(f"topic-{cat.pk}"),
            conteudo=fake.paragraph(),
            autor=autor,
            publico_alvo=0,
        )
        topicos.append(topico)
    TopicoDiscussao.objects.bulk_create(topicos)
    topicos = list(TopicoDiscussao.objects.filter(categoria__in=categorias))

    for topico in topicos:
        for _ in range(2):
            respostas.append(
                RespostaDiscussao(
                    topico=topico,
                    autor=random.choice(autores),
                    conteudo=fake.sentence(),
                )
            )
    RespostaDiscussao.objects.bulk_create(respostas)
    return categorias, topicos


def create_empresas(orgs: list[Organizacao], usuarios: list[User]) -> list[Empresa]:
    empresas: list[Empresa] = []
    for org in orgs:
        user = random.choice([u for u in usuarios if u.organizacao_id == org.id])
        empresas.append(
            Empresa(
                usuario=user,
                organizacao=org,
                razao_social=fake.company(),
                nome_fantasia=fake.company_suffix(),
                cnpj=cnpj.generate(),
                ramo_atividade=fake.job(),
                endereco=fake.street_address(),
                cidade=fake.city(),
                estado=fake.state_abbr(),
                cep=fake.postcode(),
                email_corporativo=fake.company_email(),
                telefone_corporativo=fake.phone_number(),
                site=fake.url(),
                rede_social=fake.url(),
            )
        )
    Empresa.objects.bulk_create(empresas)
    return empresas


def create_parcerias(eventos: list[Evento], empresas: list[Empresa]):
    from agenda.models import ParceriaEvento

    parcerias: list[ParceriaEvento] = []
    for evento in eventos:
        empresa = random.choice(empresas)
        parcerias.append(
            ParceriaEvento(
                evento=evento,
                nucleo=evento.nucleo,
                empresa=empresa,
                whatsapp_contato=fake.msisdn(),
                data_inicio=timezone.now().date(),
                data_fim=timezone.now().date() + timezone.timedelta(days=30),
                descricao=fake.sentence(),
            )
        )
    ParceriaEvento.objects.bulk_create(parcerias)
    return parcerias


def create_tokens(usuarios: list[User]) -> list[TokenAcesso]:
    tokens: list[TokenAcesso] = []
    for user in usuarios:
        # pulamos usuários root/superadmin, pois não necessitam de token
        if user.is_superuser:
            continue
        try:
            tipo_enum = TokenAcesso.TipoUsuario[user.user_type.upper()]
        except KeyError:
            # se o tipo não existir (ex.: valor inesperado), não criamos token
            continue
        tokens.append(
            TokenAcesso(
                gerado_por=user,
                usuario=user,
                organizacao=user.organizacao,
                tipo_destino=tipo_enum,
                data_expiracao=timezone.now() + timezone.timedelta(days=30),
            )
        )
    TokenAcesso.objects.bulk_create(tokens)
    return tokens


def main() -> None:
    with transaction.atomic():
        clear_test_data()
        orgs = create_organizacoes()
        nucleos = create_nucleos(orgs)
        users, creds = create_users(orgs, nucleos)
        coordenadores = [u for u in users if u.user_type == UserType.COORDENADOR]
        eventos = create_eventos(nucleos, coordenadores)
        participantes = [u for u in users if u.user_type in {UserType.NUCLEADO, UserType.ASSOCIADO, UserType.CONVIDADO}]
        inscricoes = create_inscricoes(eventos, participantes)
        posts = create_feed(orgs, users)
        convs, msgs = create_chat(orgs, users)
        categorias, topicos = create_discussao(orgs, users)
        empresas = create_empresas(orgs, users)
        parcerias = create_parcerias(eventos, empresas)
        tokens = create_tokens(users)

    usuarios_md = os.path.join(os.path.dirname(__file__), "usuarios.md")
    with open(usuarios_md, "w", encoding="utf-8") as f:
        f.write("# Usuários criados\n\n")
        f.write("| Usuário | E-mail | Senha |\n")
        f.write("|--------|--------|------|\n")
        for usuario, email, senha in creds:
            f.write(f"| {usuario} | {email} | {senha} |\n")

    print(
        f"Organizacoes:{len(orgs)} nucleos:{len(nucleos)} usuarios:{len(users)} "
        f"eventos:{len(eventos)} inscricoes:{len(inscricoes)} posts:{len(posts)} "
        f"conversas:{len(convs)} mensagens:{len(msgs)} topicos:{len(topicos)} "
        f"empresas:{len(empresas)} parcerias:{len(parcerias)} tokens:{len(tokens)}"
    )


if __name__ == "__main__":
    main()
