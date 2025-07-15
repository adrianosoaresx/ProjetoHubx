from django import forms
from django.contrib.auth import get_user_model

from .models import TokenAcesso

User = get_user_model()


class TokenAcessoForm(forms.ModelForm):
    class Meta:
        model = TokenAcesso
        fields = ["tipo_destino"]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if user and user.tipo_id == User.Tipo.SUPERADMIN:
            self.fields["tipo_destino"].choices = [(TokenAcesso.Tipo.ADMIN, "admin")]
        elif user:
            self.fields["tipo_destino"].choices = [
                (TokenAcesso.Tipo.GERENTE, "gerente"),
                (TokenAcesso.Tipo.CLIENTE, "cliente"),
            ]

    def clean(self):
        cleaned = super().clean()
        if (
            self.user
            and self.user.tipo_id == User.Tipo.ADMIN
            and cleaned.get("tipo_destino")
            in {TokenAcesso.Tipo.GERENTE, TokenAcesso.Tipo.CLIENTE}
        ):
            self.add_error("nucleo_destino", "Selecione um núcleo")
        return cleaned
