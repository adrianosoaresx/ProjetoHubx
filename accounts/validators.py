from __future__ import annotations

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
        return _(
            "A senha deve conter pelo menos 8 caracteres, incluindo letras, números e caracteres especiais."
        )
