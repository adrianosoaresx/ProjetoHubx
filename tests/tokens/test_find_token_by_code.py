import base64
import hashlib
import secrets

import pytest

from accounts.factories import UserFactory
from accounts.models import UserType
from tokens.models import TokenAcesso
from tokens.services import create_invite_token, find_token_by_code

pytestmark = pytest.mark.django_db


def test_find_token_by_code_uses_hash():
    user = UserFactory(user_type=UserType.ADMIN.value)
    token, codigo = create_invite_token(
        gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO
    )
    encontrado = find_token_by_code(codigo)
    assert encontrado.id == token.id


def test_find_token_by_code_legacy():
    user = UserFactory(user_type=UserType.ADMIN.value)
    codigo = TokenAcesso.generate_code()
    token = TokenAcesso(gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", codigo.encode(), salt, 120000)
    token.codigo_salt = base64.b64encode(salt).decode()
    token.codigo_hash = base64.b64encode(digest).decode()
    token.save()
    encontrado = find_token_by_code(codigo)
    assert encontrado.id == token.id
