from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import MediaTag, UserMedia


class PortfolioFilterForm(forms.Form):
    q = forms.CharField(
        label=_("Buscar"),
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": _("Buscar por descrição ou tags...")}
        ),
    )


class MediaForm(forms.ModelForm):
    tags_field = forms.CharField(
        required=False,
        help_text="Separe as tags por vírgula",
        label="Tags",
    )

    class Meta:
        model = UserMedia
        fields = ("file", "descricao", "publico", "tags_field")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(
                self.instance.tags.values_list("nome", flat=True)
            )

    def save(self, commit: bool = True) -> UserMedia:
        instance = super().save(commit=False)
        if commit:
            instance.save()

        tags_field = self.cleaned_data.get("tags_field", "")
        tags_names: list[str] = []
        for tag_name in tags_field.split(","):
            name = tag_name.strip().lower()
            if name and name not in tags_names:
                tags_names.append(name)

        tags: list[MediaTag] = []
        for name in tags_names:
            tag, _ = MediaTag.objects.get_or_create(
                nome__iexact=name, defaults={"nome": name}
            )
            tags.append(tag)

        if commit:
            instance.tags.set(tags)
            self.save_m2m()
        else:
            self._save_m2m = lambda: instance.tags.set(tags)

        return instance
