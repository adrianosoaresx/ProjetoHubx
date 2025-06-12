from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class CustomUserCreationForm(UserCreationForm):
    """Formulário de criação de usuário compatível com o modelo customizado."""

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")
