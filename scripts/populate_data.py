"""
Script to populate the Hubx SQLite database with sample data.

This script inserts a root user, two administrative users, two
organizations, nuclei for each organization, several categories of users
(associates, nucleated members and guests), a few sample events and
financial records spanning three months.  All dates are generated
relative to the current time and the generated UUIDs are stored in
their canonical hex form (without hyphens) to match the database
schema.

To run the script simply execute it with a Python interpreter.  It
expects the ``db.sqlite3`` file to be located in the same directory
as the script.  Running the script repeatedly will append additional
records; it does not attempt to remove existing entries.
"""

import base64
import hashlib
import os
import secrets
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timedelta


def slugify(value: str) -> str:
    """Simplify a string to a slug.

    Accented characters are stripped, the result is lower‑case and
    spaces are replaced by hyphens.  Non alphanumeric characters (with
    the exception of hyphens) are removed.
    """
    # Normalize unicode characters to their canonical form and strip accents
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    lowered = normalized.lower().replace(" ", "-")
    # Remove any character that isn't alphanumeric or a hyphen
    slug = "".join(ch for ch in lowered if ch.isalnum() or ch == "-")
    return slug


def make_password(raw_password: str) -> str:
    """Return a Django compatible PBKDF2 SHA256 password hash.

    The resulting string has the format
    ``pbkdf2_sha256$<iterations>$<salt>$<hash>``.  A random 16
    character salt is generated for each call.
    """
    iterations = 260000
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", raw_password.encode(), salt.encode(), iterations)
    # Django encodes the digest in base64 without padding
    hash_b64 = base64.b64encode(dk).decode().strip()
    return f"pbkdf2_sha256${iterations}${salt}${hash_b64}"


def insert_user(cur, user_data: dict) -> int:
    """Insert a user into the accounts_user table and return its id.

    ``user_data`` should contain all mandatory columns; fields not
    specified will be set to sensible defaults.  The current
    timestamp is used for ``date_joined``, ``created_at`` and
    ``updated_at``.  A freshly generated password hash is used if
    ``password`` is omitted.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    password = user_data.get("password") or make_password("password123")
    first_name = user_data.get("first_name", "")
    last_name = user_data.get("last_name", "")
    email = user_data["email"]
    username = user_data["username"]
    is_staff = 1 if user_data.get("is_staff") else 0
    is_superuser = 1 if user_data.get("is_superuser") else 0
    is_active = 1
    user_type = user_data.get("user_type", "convidado")
    is_associado = 1 if user_data.get("is_associado") else 0
    is_coordenador = 1 if user_data.get("is_coordenador") else 0
    organizacao_id = user_data.get("organizacao_id")
    nucleo_id = user_data.get("nucleo_id")
    # Default string fields (not nullable) – use empty strings unless provided
    defaults = {
        "biografia": "",
        "phone_number": "",
        "whatsapp": "",
        "endereco": "",
        "cidade": user_data.get("cidade", ""),
        "estado": user_data.get("estado", ""),
        "cep": user_data.get("cep", "00000-000"),
        "idioma": "pt-BR",
        "fuso_horario": "America/Sao_Paulo",
        "perfil_publico": 1,
        "mostrar_email": 1,
        "mostrar_telefone": 0,
        "exclusao_confirmada": 0,
        "two_factor_enabled": 0,
        "email_confirmed": 0,
    }
    # Prepare insert statement
    columns = [
        "password",
        "last_login",
        "is_superuser",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
        "created_at",
        "updated_at",
        "deleted",
        "deleted_at",
        "email",
        "phone_number",
        "birth_date",
        "cpf",
        "biografia",
        "cover",
        "whatsapp",
        "avatar",
        "endereco",
        "cidade",
        "estado",
        "cep",
        "redes_sociais",
        "idioma",
        "fuso_horario",
        "perfil_publico",
        "mostrar_email",
        "mostrar_telefone",
        "chave_publica",
        "exclusao_confirmada",
        "two_factor_enabled",
        "two_factor_secret",
        "email_confirmed",
        "user_type",
        "is_associado",
        "is_coordenador",
        "nucleo_id",
        "organizacao_id",
        "username",
    ]
    values = [
        password,
        None,  # last_login
        is_superuser,
        first_name,
        last_name,
        is_staff,
        is_active,
        now,  # date_joined
        now,  # created_at
        now,  # updated_at
        0,  # deleted
        None,  # deleted_at
        email,
        defaults["phone_number"],
        None,  # birth_date
        None,  # cpf
        defaults["biografia"],
        None,  # cover
        defaults["whatsapp"],
        None,  # avatar
        defaults["endereco"],
        defaults["cidade"],
        defaults["estado"],
        defaults["cep"],
        None,  # redes_sociais JSON
        defaults["idioma"],
        defaults["fuso_horario"],
        defaults["perfil_publico"],
        defaults["mostrar_email"],
        defaults["mostrar_telefone"],
        None,  # chave_publica
        defaults["exclusao_confirmada"],
        defaults["two_factor_enabled"],
        None,  # two_factor_secret
        defaults["email_confirmed"],
        user_type,
        is_associado,
        is_coordenador,
        nucleo_id,
        organizacao_id,
        username,
    ]
    placeholders = ", ".join(["?" for _ in columns])
    sql = f"INSERT INTO accounts_user ({', '.join(columns)}) VALUES ({placeholders})"
    cur.execute(sql, values)
    return cur.lastrowid


def insert_organizacao(cur, data: dict) -> str:
    """Insert an organization and return its 32‑character UUID string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    org_id = uuid.uuid4().hex
    nome = data["nome"]
    slug = slugify(nome)
    cnpj = data.get("cnpj", "00.000.000/0000-00")
    tipo = data.get("tipo", "ong")
    rua = data.get("rua", "")
    cidade = data.get("cidade", "")
    estado = data.get("estado", "")
    contato_nome = data.get("contato_nome", "")
    contato_email = data.get("contato_email", "")
    contato_telefone = data.get("contato_telefone", "")
    created_by_id = data.get("created_by_id")
    descricao = data.get("descricao", "")
    indice_reajuste = data.get("indice_reajuste", 0)
    rate_limit_multiplier = data.get("rate_limit_multiplier", 1)
    cur.execute(
        """
        INSERT INTO organizacoes_organizacao (
            created_at, updated_at, deleted, deleted_at, id, nome, cnpj, descricao,
            slug, tipo, rua, cidade, estado, contato_nome, contato_email,
            contato_telefone, avatar, cover, rate_limit_multiplier, created_by_id,
            indice_reajuste, inativa, inativada_em
        ) VALUES (?, ?, 0, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, 0, NULL)
        """,
        (
            now,
            now,
            org_id,
            nome,
            cnpj,
            descricao,
            slug,
            tipo,
            rua,
            cidade,
            estado,
            contato_nome,
            contato_email,
            contato_telefone,
            rate_limit_multiplier,
            created_by_id,
            indice_reajuste,
        ),
    )
    return org_id


def insert_nucleo(cur, org_id: str, nome: str) -> int:
    """Insert a nucleus associated with the given organization and return its integer id."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = slugify(nome)
    descricao = ""
    mensalidade = 30.0
    ativo = 1
    cur.execute(
        """
        INSERT INTO nucleos_nucleo (
            created_at, updated_at, deleted, deleted_at, nome, slug, descricao,
            avatar, cover, mensalidade, organizacao, ativo
        ) VALUES (?, ?, 0, NULL, ?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (
            now,
            now,
            nome,
            slug,
            descricao,
            mensalidade,
            org_id,
            ativo,
        ),
    )
    return cur.lastrowid


def insert_participacao_nucleo(cur, user_id: int, nucleo_id: int):
    """Link a user to a nucleus with active membership."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO nucleos_participacaonucleo (
            created_at, updated_at, deleted, deleted_at, status,
            data_solicitacao, data_decisao, justificativa, decidido_por_id,
            nucleo_id, user_id, papel, status_suspensao, data_suspensao
        ) VALUES (?, ?, 0, NULL, ?, ?, NULL, ?, NULL, ?, ?, ?, 0, NULL)
        """,
        (
            now,
            now,
            "ativo",
            now,
            "",  # justificativa
            nucleo_id,
            user_id,
            "membro",
        ),
    )


def insert_event(cur, data: dict) -> str:
    """Insert an event and return its UUID string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_id = uuid.uuid4().hex
    titulo = data["titulo"]
    descricao = data.get("descricao", "")
    data_inicio = data["data_inicio"]
    data_fim = data["data_fim"]
    local = data.get("local", "")
    cidade = data.get("cidade", "")
    estado = data.get("estado", "")
    cep = data.get("cep", "00000-000")
    status = data.get("status", 0)
    publico_alvo = data.get("publico_alvo", 0)
    numero_convidados = data.get("numero_convidados", 0)
    numero_presentes = data.get("numero_presentes", 0)
    valor_ingresso = data.get("valor_ingresso")
    orcamento = data.get("orcamento")
    orcamento_estimado = data.get("orcamento_estimado")
    valor_gasto = data.get("valor_gasto")
    participantes_maximo = data.get("participantes_maximo")
    espera_habilitada = 1 if data.get("espera_habilitada") else 0
    cronograma = data.get("cronograma", "")
    informacoes_adicionais = data.get("informacoes_adicionais", "")
    contato_nome = data.get("contato_nome", "")
    contato_email = data.get("contato_email", "")
    contato_whatsapp = data.get("contato_whatsapp", "")
    coordenador_id = data["coordenador_id"]
    nucleo_id = data.get("nucleo_id")
    organizacao_id = data["organizacao_id"]
    cur.execute(
        """
        INSERT INTO agenda_evento (
            deleted, deleted_at, id, titulo, descricao, data_inicio, data_fim,
            local, cidade, estado, cep, status, publico_alvo, numero_convidados,
            numero_presentes, valor_ingresso, orcamento, orcamento_estimado,
            valor_gasto, participantes_maximo, espera_habilitada, cronograma,
            informacoes_adicionais, contato_nome, contato_email, contato_whatsapp,
            avatar, cover, briefing, coordenador_id, mensagem_origem_id, nucleo_id,
            organizacao_id, created_at, updated_at
        ) VALUES (
            0, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL,
            ?, NULL, ?, ?, ?, ?
        )
        """,
        (
            event_id,
            titulo,
            descricao,
            data_inicio,
            data_fim,
            local,
            cidade,
            estado,
            cep,
            status,
            publico_alvo,
            numero_convidados,
            numero_presentes,
            valor_ingresso,
            orcamento,
            orcamento_estimado,
            valor_gasto,
            participantes_maximo,
            espera_habilitada,
            cronograma,
            informacoes_adicionais,
            contato_nome,
            contato_email,
            contato_whatsapp,
            coordenador_id,
            nucleo_id,
            organizacao_id,
            now,
            now,
        ),
    )
    return event_id


def insert_centro_custo(cur, org_id: str, nome: str = "Centro de Custo") -> str:
    """Insert a cost centre tied to an organization and return its UUID string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cc_id = uuid.uuid4().hex
    tipo = "organizacao"
    saldo = 0.0
    cur.execute(
        """
        INSERT INTO financeiro_centrocusto (
            created_at, updated_at, deleted, deleted_at, id, nome, tipo, saldo,
            evento_id, nucleo_id, organizacao_id, descricao
        ) VALUES (?, ?, 0, NULL, ?, ?, ?, ?, NULL, NULL, ?, "")
        """,
        (
            now,
            now,
            cc_id,
            nome,
            tipo,
            saldo,
            org_id,
        ),
    )
    return cc_id


def insert_lancamento(cur, cc_id: str, data: dict) -> str:
    """Insert a financial entry (lancamento) tied to a cost centre and return its UUID string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lanc_id = uuid.uuid4().hex
    tipo = data["tipo"]
    valor = data["valor"]
    data_lancamento = data["data_lancamento"]
    data_vencimento = data.get("data_vencimento", data_lancamento)
    status = data.get("status", "pendente")
    origem = data.get("origem", "manual")
    descricao = data.get("descricao", "")
    conta_associado_id = data.get("conta_associado_id")
    originador_id = data.get("originador_id")
    ajustado = 0
    cur.execute(
        """
        INSERT INTO financeiro_lancamentofinanceiro (
            created_at, updated_at, deleted, deleted_at, id, tipo, valor,
            data_lancamento, data_vencimento, status, descricao, ultima_notificacao,
            ajustado, centro_custo_id, conta_associado_id, originador_id, origem,
            lancamento_original_id
        ) VALUES (?, ?, 0, NULL, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, NULL)
        """,
        (
            now,
            now,
            lanc_id,
            tipo,
            valor,
            data_lancamento,
            data_vencimento,
            status,
            descricao,
            ajustado,
            cc_id,
            conta_associado_id,
            originador_id,
            origem,
        ),
    )
    return lanc_id


def update_centro_custo_saldo(cur, cc_id: str):
    """Recalculate and update the saldo for a cost centre based on its entries."""
    # Sum all positive (incomes) minus negative (expenses) values where DELETED flag is 0
    # Expenses are indicated by tipo 'despesa'; all other types increase the saldo.
    cur.execute(
        """
        SELECT tipo, SUM(valor) FROM financeiro_lancamentofinanceiro
        WHERE centro_custo_id = ? AND deleted = 0
        GROUP BY tipo
        """,
        (cc_id,),
    )
    result = cur.fetchall()
    saldo = 0.0
    for t, total in result:
        if t == "despesa":
            saldo -= float(total)
        else:
            saldo += float(total)
    cur.execute(
        "UPDATE financeiro_centrocusto SET saldo = ?, updated_at = ? WHERE id = ?",
        (saldo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cc_id),
    )


def main():
    db_path = os.path.join(os.path.dirname(__file__), "db.sqlite3")
    conn = sqlite3.connect(db_path)
    # Enable foreign key enforcement
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Create root user
    insert_user(
        cur,
        {
            "email": "root@hubx.com.br",
            "username": "root",
            "first_name": "Root",
            "last_name": "User",
            "is_staff": True,
            "is_superuser": True,
            "user_type": "root",
        },
    )

    # Create two admin users
    admin1_id = insert_user(
        cur,
        {
            "email": "admin1@hubx.com.br",
            "username": "admin1",
            "first_name": "Admin",
            "last_name": "One",
            "is_staff": True,
            "is_superuser": False,
            "user_type": "admin",
        },
    )
    admin2_id = insert_user(
        cur,
        {
            "email": "admin2@hubx.com.br",
            "username": "admin2",
            "first_name": "Admin",
            "last_name": "Two",
            "is_staff": True,
            "is_superuser": False,
            "user_type": "admin",
        },
    )

    # Create organizations
    orgs = []
    orgs.append(
        {
            "nome": "CDL FLORIANOPOLIS",
            "cidade": "Florianópolis",
            "estado": "SC",
            "cnpj": "00.000.000/0001-91",
            "tipo": "ong",
            "created_by_id": admin1_id,
        }
    )
    orgs.append(
        {
            "nome": "CDL BLUMENAU",
            "cidade": "Blumenau",
            "estado": "SC",
            "cnpj": "00.000.000/0002-72",
            "tipo": "ong",
            "created_by_id": admin2_id,
        }
    )
    org_ids = []
    for org_data in orgs:
        org_id = insert_organizacao(cur, org_data)
        org_ids.append(org_id)

    # Map organization to its admins
    org_admins = {org_ids[0]: admin1_id, org_ids[1]: admin2_id}

    # Create nuclei and cost centres
    nucleo_ids_per_org = {}
    cost_centre_ids = {}
    for org_id in org_ids:
        nucleo_ids = []
        for nome in ["NUCLEO DA MULHER", "NUCLEO DE TECNOLOGIA"]:
            nucleo_id = insert_nucleo(cur, org_id, nome)
            nucleo_ids.append(nucleo_id)
        nucleo_ids_per_org[org_id] = nucleo_ids
        # Create a cost centre for the organization
        cc_id = insert_centro_custo(cur, org_id, nome="Centro de Custo Principal")
        cost_centre_ids[org_id] = cc_id

    # Create events (3 per organization)
    for org_index, org_id in enumerate(org_ids):
        admin_id = org_admins[org_id]
        nucleo_ids = nucleo_ids_per_org[org_id]
        for i in range(3):
            start_date = (datetime.now() + timedelta(days=30 * (i + 1))).strftime("%Y-%m-%d %H:%M:%S")
            end_date = (datetime.now() + timedelta(days=30 * (i + 1), hours=2)).strftime("%Y-%m-%d %H:%M:%S")
            event_data = {
                "titulo": f"Evento {i + 1} - {orgs[org_index]['nome']}",
                "descricao": "Evento de demonstração gerado pelo script de dados.",
                "data_inicio": start_date,
                "data_fim": end_date,
                "local": "Auditório",
                "cidade": orgs[org_index]["cidade"],
                "estado": orgs[org_index]["estado"],
                "cep": "88000-000" if org_index == 0 else "89000-000",
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
                "contato_email": f"contato@{slugify(orgs[org_index]['nome'])}.com",
                "contato_whatsapp": "",
                "coordenador_id": admin_id,
                "nucleo_id": nucleo_ids[i % len(nucleo_ids)],
                "organizacao_id": org_id,
            }
            insert_event(cur, event_data)

    # Create users for each organization
    for org_index, org_id in enumerate(org_ids):
        nucleo_ids = nucleo_ids_per_org[org_id]
        # 50 associates (is_associado=True, user_type=associado) without nucleus
        for i in range(50):
            user_id = insert_user(
                cur,
                {
                    "email": f"assoc{i + 1}@{slugify(orgs[org_index]['nome'])}.com",
                    "username": f"assoc{i + 1}_{org_index + 1}",
                    "first_name": "Associado",
                    "last_name": f"{i + 1}",
                    "is_staff": False,
                    "is_superuser": False,
                    "user_type": "associado",
                    "is_associado": True,
                    "is_coordenador": False,
                    "organizacao_id": org_id,
                    "cidade": orgs[org_index]["cidade"],
                    "estado": orgs[org_index]["estado"],
                },
            )
            # Create a financial account for the associate with zero balance
            cur.execute(
                """
                INSERT INTO financeiro_contaassociado (
                    created_at, updated_at, deleted, deleted_at, id, saldo, user_id
                ) VALUES (?, ?, 0, NULL, ?, 0.0, ?)
                """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    uuid.uuid4().hex,
                    user_id,
                ),
            )
        # 30 nucleated members (is_associado=True, user_type=nucleado) assigned to a nucleus
        for i in range(30):
            nucleo_id = nucleo_ids[i % len(nucleo_ids)]
            user_id = insert_user(
                cur,
                {
                    "email": f"nucleado{i + 1}@{slugify(orgs[org_index]['nome'])}.com",
                    "username": f"nucleado{i + 1}_{org_index + 1}",
                    "first_name": "Nucleado",
                    "last_name": f"{i + 1}",
                    "is_staff": False,
                    "is_superuser": False,
                    "user_type": "nucleado",
                    "is_associado": True,
                    "is_coordenador": False,
                    "organizacao_id": org_id,
                    "nucleo_id": nucleo_id,
                    "cidade": orgs[org_index]["cidade"],
                    "estado": orgs[org_index]["estado"],
                },
            )
            # Link to nucleus participation table
            insert_participacao_nucleo(cur, user_id, nucleo_id)
            # Create a financial account for the nucleated associate
            cur.execute(
                """
                INSERT INTO financeiro_contaassociado (
                    created_at, updated_at, deleted, deleted_at, id, saldo, user_id
                ) VALUES (?, ?, 0, NULL, ?, 0.0, ?)
                """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    uuid.uuid4().hex,
                    user_id,
                ),
            )
        # 5 guests (user_type=convidado) – not associated
        for i in range(5):
            insert_user(
                cur,
                {
                    "email": f"convidado{i + 1}@{slugify(orgs[org_index]['nome'])}.com",
                    "username": f"convidado{i + 1}_{org_index + 1}",
                    "first_name": "Convidado",
                    "last_name": f"{i + 1}",
                    "is_staff": False,
                    "is_superuser": False,
                    "user_type": "convidado",
                    "is_associado": False,
                    "is_coordenador": False,
                    # Convidados não pertencem a nenhuma organização nem núcleo
                    "organizacao_id": None,
                    "nucleo_id": None,
                    "cidade": orgs[org_index]["cidade"],
                    "estado": orgs[org_index]["estado"],
                },
            )

    # Insert financial records (3 months) for each organization
    for org_id in org_ids:
        cc_id = cost_centre_ids[org_id]
        # We'll generate records for the last three months relative to today
        today = datetime.now()
        for month_offset in range(3, 0, -1):
            date_ref = today - timedelta(days=30 * month_offset)
            # Income (ex: aporte_externo)
            insert_lancamento(
                cur,
                cc_id,
                {
                    "tipo": "aporte_externo",
                    "valor": 5000.00,
                    "data_lancamento": date_ref.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "pago",
                    "descricao": f"Aporte externo referente ao mês {date_ref.strftime('%Y-%m')}",
                },
            )
            # Expense (despesa)
            insert_lancamento(
                cur,
                cc_id,
                {
                    "tipo": "despesa",
                    "valor": 2000.00,
                    "data_lancamento": (date_ref + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "pago",
                    "descricao": f"Despesa operacional referente ao mês {date_ref.strftime('%Y-%m')}",
                },
            )
        # After inserting all records for the organisation, update its cost centre saldo
        update_centro_custo_saldo(cur, cc_id)

    # Commit all changes
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()