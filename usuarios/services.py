"""Serviços de manipulação de usuários."""

from usuarios.models import Usuario



def create_user(username, email, password, first_name="", last_name=""):
    """Cria um novo usuário se o nome de usuário ainda não existir."""

    if Usuario.objects.filter(username=username).exists():
        return None

    user = Usuario.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    return user
