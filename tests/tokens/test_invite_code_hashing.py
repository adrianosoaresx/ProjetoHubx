import hashlib
import pytest

from accounts.factories import UserFactory
from accounts.models import UserType
from tokens.models import TokenAcesso
from tokens.services import create_invite_token

pytestmark = pytest.mark.django_db


def test_invite_code_hashing():
    user = UserFactory(user_type=UserType.ADMIN.value)
    token, codigo = create_invite_token(
        gerado_por=user,
        tipo_destino=TokenAcesso.TipoUsuario.CONVIDADO.value,
    )
    assert token.check_codigo(codigo)
    assert not token.check_codigo("wrong")
    assert len(codigo) >= 32
    assert codigo not in token.codigo_hash
    assert token.codigo_hash == hashlib.sha256(codigo.encode()).hexdigest()
    assert len(token.codigo_hash) == 64
    assert "codigo" not in [f.name for f in TokenAcesso._meta.fields]
