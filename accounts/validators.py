import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ComplexPasswordValidator:
    """Validator that requires at least 8 characters, letters, numbers and special chars."""

    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(
                _("Esta senha é muito curta. Ela deve conter pelo menos 8 caracteres."),
                code="password_too_short",
            )
        if not re.search(r"[A-Za-z]", password):
            raise ValidationError(
                _("A senha deve conter letras."),
                code="password_no_letter",
            )
        if not re.search(r"\d", password):
            raise ValidationError(
                _("A senha deve conter números."),
                code="password_no_number",
            )
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError(
                _("A senha deve conter caracteres especiais."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _("A senha deve conter pelo menos 8 caracteres, incluindo letras, números e caracteres especiais.")


def cpf_validator(value: str) -> None:
    """Valida o CPF utilizando os dígitos verificadores oficiais."""
    cpf = re.sub(r"\D", "", value or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError(_("Digite um CPF válido no formato 000.000.000-00."))

    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[i]):
            raise ValidationError(_("Digite um CPF válido no formato 000.000.000-00."))
