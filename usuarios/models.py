from django.contrib.auth.models import User

class Usuario(User):
    """Proxy model para utilizar o usuário padrão do Django."""

    class Meta:
        proxy = True
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
