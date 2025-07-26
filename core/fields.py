from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


class URLField(models.URLField):
    """URLField with default https scheme."""

    def __init__(self, *args, assume_scheme="https", **kwargs):
        self.assume_scheme = assume_scheme
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {"assume_scheme": self.assume_scheme}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class EncryptedCharField(models.CharField):
    """CharField that stores values encrypted using Fernet."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = Fernet(settings.FERNET_KEY)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        if isinstance(value, str) and value.startswith("gAAAA"):
            return value
        return self._fernet.encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            return value

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        if isinstance(value, str) and value.startswith("gAAAA"):
            try:
                return self._fernet.decrypt(value.encode()).decode()
            except InvalidToken:
                return value
        return value
