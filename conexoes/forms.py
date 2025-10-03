from django import forms
from django.utils.translation import gettext_lazy as _


class ConnectionsSearchForm(forms.Form):
    q = forms.CharField(label=_("Buscar"), max_length=255, required=False)

    def __init__(
        self,
        *args,
        placeholder: str | None = None,
        label: str | None = None,
        aria_label: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        field = self.fields["q"]
        if label:
            field.label = label
        field.widget.attrs.setdefault("autocomplete", "off")
        if placeholder:
            field.widget.attrs["placeholder"] = placeholder
        if aria_label:
            field.widget.attrs["aria-label"] = aria_label
