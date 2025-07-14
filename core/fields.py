from django.db import models
from django.forms import URLField as FormURLField


class URLField(models.URLField):
    """URLField with default https scheme."""

    def __init__(self, *args, assume_scheme="https", **kwargs):
        self.assume_scheme = assume_scheme
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {"assume_scheme": self.assume_scheme}
        defaults.update(kwargs)
        return super().formfield(**defaults)

