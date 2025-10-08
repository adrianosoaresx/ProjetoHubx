"""Ferramentas para preparar o ambiente do núcleo CDL Mulher.

Este script reinicializa o banco de dados (SQLite ou PostgreSQL) e
reconstrói os dados essenciais necessários para o núcleo "Núcleo da Mulher"
da organização "Câmara de Dirigentes Lojistas de Florianópolis". Ele também
importa os integrantes definidos no arquivo JSON
``scripts/membros_nucleo_cdl_mulher.json``.

Uso:

    python scripts/setup_cdl_mulher.py --engine <sqlite|postgres>

Opcionalmente é possível definir uma senha padrão para os membros via
``--member-password`` ou variável de ambiente
``CDL_MULHER_MEMBER_PASSWORD``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

import django


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Setup do núcleo CDL Mulher")
    parser.add_argument(
        "--engine",
        required=True,
        choices={"sqlite", "postgres"},
        help="Define o banco a ser reinicializado",
    )
    parser.add_argument(
        "--member-password",
        default=os.environ.get("CDL_MULHER_MEMBER_PASSWORD", "Hubx123!"),
        help="Senha padrão atribuída aos membros importados",
    )
    return parser.parse_args()


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def ensure_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()


def close_connections() -> None:
    from django.db import connections

    connections.close_all()


def reset_sqlite(db_config: dict[str, Any]) -> None:
    db_path = Path(db_config["NAME"]).resolve()
    if db_path.exists():
        db_path.unlink()
        print(f"Arquivo SQLite removido: {db_path}")
    else:
        print(f"Arquivo SQLite não encontrado (ignorado): {db_path}")


def reset_postgres(db_config: dict[str, Any]) -> None:
    import psycopg2
    from psycopg2 import sql

    name = db_config.get("NAME")
    if not name:
        raise RuntimeError("DATABASES['default']['NAME'] não configurado para PostgreSQL")

    params: dict[str, Any] = {
        "dbname": db_config.get("OPTIONS", {}).get("dbname", "postgres"),
        "user": db_config.get("USER"),
        "password": db_config.get("PASSWORD"),
        "host": db_config.get("HOST") or None,
        "port": db_config.get("PORT") or None,
    }

    if params["dbname"] == name:
        params["dbname"] = "postgres"

    params = {k: v for k, v in params.items() if v not in {None, ""}}

    print(f"Reconstruindo banco PostgreSQL '{name}'")
    with psycopg2.connect(**params) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid();
                """,
                (name,),
            )
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}" ).format(sql.Identifier(name)))
            owner = db_config.get("USER")
            if owner:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(name), sql.Identifier(owner)
                    )
                )
            else:
                cursor.execute(sql.SQL("CREATE DATABASE {}" ).format(sql.Identifier(name)))
    print("Banco PostgreSQL recriado com sucesso.")


def run_migrations() -> None:
    from django.core.management import call_command

    call_command("migrate", interactive=False)


def load_members_data() -> list[dict[str, Any]]:
    json_path = Path(__file__).resolve().parent / "membros_nucleo_cdl_mulher.json"
    with json_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise RuntimeError("Arquivo JSON de membros deve conter uma lista de registros")
    return [row for row in data if isinstance(row, dict)]


USERNAME_CLEAN_RE = re.compile(r"[^a-z0-9.+-_]")


def normalize_username(value: str | None) -> str:
    if not value:
        return "usuario"
    cleaned = USERNAME_CLEAN_RE.sub("", value.lower())
    return cleaned or "usuario"


def generate_unique_username(preferred: str, exclude_pk: Optional[Any] = None) -> str:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    base = normalize_username(preferred)
    candidate = base
    suffix = 1
    while True:
        qs = User.all_objects.filter(username=candidate)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return candidate
        candidate = f"{base}{suffix}"
        suffix += 1


def sanitize_digits(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


def ensure_exact_username(user, desired: str) -> None:
    model = user.__class__
    conflict = model.all_objects.exclude(pk=user.pk).filter(username=desired).first()
    if conflict:
        conflict.username = generate_unique_username(f"{desired}-usuario", exclude_pk=conflict.pk)
        conflict.save(update_fields=["username"])
    if user.username != desired:
        user.username = desired
        user.save(update_fields=["username"])


def ensure_unique_slug(model, base_slug: str, instance=None) -> str:
    slug = base_slug or "organizacao"
    if hasattr(model, "all_objects"):
        queryset = model.all_objects
    else:
        queryset = model.objects

    pk = getattr(instance, "pk", None)
    final_slug = slug
    counter = 1
    while queryset.filter(slug=final_slug).exclude(pk=pk).exists():
        counter += 1
        final_slug = f"{slug}-{counter}"
    return final_slug


def upsert_user(
    *,
    email: str,
    preferred_username: str,
    base_defaults: dict[str, Any],
    password: str | None = None,
) -> Tuple[Any, bool]:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.all_objects.filter(email=email).first()
    created = False
    if user is None:
        created = True
        username = generate_unique_username(preferred_username)
        user = User(email=email, username=username)
    elif not user.username:
        user.username = generate_unique_username(preferred_username, exclude_pk=user.pk)

    changed = False
    for field, value in base_defaults.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True

    if getattr(user, "deleted", False):
        user.deleted = False
        user.deleted_at = None
        changed = True

    if password is not None:
        user.set_password(password)
        changed = True

    if created or changed:
        user.save()

    return user, created


def upsert_participacao(user, nucleo):
    from nucleos.models import ParticipacaoNucleo

    participacao = ParticipacaoNucleo.all_objects.filter(user=user, nucleo=nucleo).first()
    created = False
    if participacao is None:
        participacao = ParticipacaoNucleo(user=user, nucleo=nucleo)
        created = True

    updated = False
    if participacao.papel != "membro":
        participacao.papel = "membro"
        updated = True
    if participacao.papel_coordenador:
        participacao.papel_coordenador = None
        updated = True
    if participacao.status != "ativo":
        participacao.status = "ativo"
        updated = True
    if participacao.status_suspensao:
        participacao.status_suspensao = False
        participacao.data_suspensao = None
        updated = True
    if getattr(participacao, "deleted", False):
        participacao.deleted = False
        participacao.deleted_at = None
        updated = True

    if created or updated:
        participacao.save()

    return created, updated


def setup_domain_objects(member_password: str) -> None:
    from django.utils.text import slugify

    from accounts.models import UserType
    from nucleos.models import ParticipacaoNucleo, Nucleo
    from organizacoes.models import Organizacao

    org_name = "Câmara de Dirigentes Lojistas de Florianópolis"
    org_cnpj = "05.078.251/0001-02"
    nucleo_name = "Núcleo da Mulher"

    base_slug = slugify(org_name)

    organizacao = Organizacao.all_objects.filter(cnpj=org_cnpj).first()
    if organizacao is None:
        slug = ensure_unique_slug(Organizacao, base_slug)
        organizacao = Organizacao(cnpj=org_cnpj, nome=org_name, slug=slug, inativa=False)
        organizacao.save()
    else:
        changed = False
        if organizacao.nome != org_name:
            organizacao.nome = org_name
            changed = True
        desired_slug = ensure_unique_slug(Organizacao, base_slug, instance=organizacao)
        if organizacao.slug != desired_slug:
            organizacao.slug = desired_slug
            changed = True
        if organizacao.inativa:
            organizacao.inativa = False
            changed = True
        if getattr(organizacao, "deleted", False):
            organizacao.deleted = False
            organizacao.deleted_at = None
            changed = True
        if changed:
            organizacao.save()

    nucleo = Nucleo.all_objects.filter(organizacao=organizacao, nome=nucleo_name).first()
    if nucleo is None:
        nucleo = Nucleo(organizacao=organizacao, nome=nucleo_name, descricao=nucleo_name, ativo=True)
        nucleo.save()
    else:
        changed = False
        if nucleo.descricao != nucleo_name:
            nucleo.descricao = nucleo_name
            changed = True
        if not nucleo.ativo:
            nucleo.ativo = True
            changed = True
        if nucleo.organizacao_id != organizacao.id:
            nucleo.organizacao = organizacao
            changed = True
        if getattr(nucleo, "deleted", False):
            nucleo.deleted = False
            nucleo.deleted_at = None
            changed = True
        if changed:
            nucleo.save()

    root_defaults = {
        "user_type": UserType.ROOT.value,
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
        "contato": "Root",
        "organizacao": None,
        "nucleo": None,
        "is_associado": False,
    }
    root_user, _ = upsert_user(
        email="root@hubx.local",
        preferred_username="root",
        base_defaults=root_defaults,
        password="J0529*435",
    )
    ensure_exact_username(root_user, "root")

    admin_defaults = {
        "user_type": UserType.ADMIN.value,
        "is_staff": True,
        "is_superuser": False,
        "is_active": True,
        "contato": "CDL Admin",
        "organizacao": organizacao,
        "nucleo": nucleo,
        "is_associado": True,
    }
    admin_user, _ = upsert_user(
        email="cdladmin@hubx.local",
        preferred_username="cdladmin",
        base_defaults=admin_defaults,
        password="pionera",
    )
    ensure_exact_username(admin_user, "cdladmin")

    members_data = load_members_data()
    created_members = 0
    updated_members = 0
    skipped = 0

    for row in members_data:
        email = (row.get("e_mail") or "").strip().lower()
        nome = (row.get("nome") or "").strip()
        if not email or not nome:
            skipped += 1
            continue

        username_base = email.split("@")[0] if email else nome
        preferred_username = normalize_username(username_base or nome)
        cpf = sanitize_digits(row.get("cpf"))
        phone = (row.get("telefone") or "").strip() or None

        user_defaults = {
            "contato": nome,
            "organizacao": organizacao,
            "nucleo": nucleo,
            "is_active": True,
            "is_associado": True,
            "user_type": UserType.NUCLEADO.value,
            "cpf": cpf,
            "razao_social": (row.get("razao_social") or "").strip() or None,
            "nome_fantasia": (row.get("nome_fantasia") or "").strip() or None,
            "whatsapp": phone,
        }

        user, created = upsert_user(
            email=email,
            preferred_username=preferred_username,
            base_defaults=user_defaults,
            password=member_password,
        )

        if created:
            created_members += 1
        else:
            updated_members += 1

        upsert_participacao(user, nucleo)

    from nucleos.models import ParticipacaoNucleo

    participacoes_ativas = ParticipacaoNucleo.objects.filter(
        nucleo=nucleo, status="ativo", status_suspensao=False
    ).count()

    print("Resumo do processamento:")

    print(f"- Usuário root senha: J0529*435")
    print(f"- Usuário admin senha: pionera")
    print(f"- Senha padrão de membros: {member_password}")

    print(f"- Membros criados: {created_members}")
    print(f"- Membros atualizados: {updated_members}")
    print(f"- Participações ativas no núcleo: {participacoes_ativas}")
    if skipped:
        print(f"- Registros ignorados por falta de dados: {skipped}")


def main() -> None:
    args = parse_args()
    ensure_django()

    from django.conf import settings

    close_connections()
    default_db = settings.DATABASES["default"]

    if args.engine == "sqlite":
        if "sqlite" not in default_db.get("ENGINE", ""):
            raise RuntimeError("Configuração atual não está usando SQLite")
        reset_sqlite(default_db)
    else:
        if "postgres" not in default_db.get("ENGINE", ""):
            raise RuntimeError("Configuração atual não está usando PostgreSQL")
        reset_postgres(default_db)

    run_migrations()
    setup_domain_objects(args.member_password)


if __name__ == "__main__":
    main()
