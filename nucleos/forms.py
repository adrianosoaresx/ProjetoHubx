from __future__ import annotations

import bleach
from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import MediaTag
from accounts.forms import ProfileImageFileInput

from .models import Nucleo, NucleoMidia, ParticipacaoNucleo

class NucleoForm(forms.ModelForm):
    class Meta:
        model = Nucleo
        fields = [
            "nome",
            "descricao",
            "classificacao",
            "avatar",
            "cover",
            "mensalidade",
            "ativo",
        ]
        labels = {
            "avatar": _("Foto do perfil"),
            "cover": _("Imagem da capa"),
        }
        widgets = {
            "avatar": ProfileImageFileInput(
                button_label=_("Enviar foto"),
                empty_label=_("Nenhuma foto selecionada"),
            ),
            "cover": ProfileImageFileInput(
                button_label=_("Enviar imagem"),
                empty_label=_("Nenhuma imagem selecionada"),
            ),
        }

    def clean_descricao(self):
        descricao = self.cleaned_data.get("descricao", "")
        return bleach.clean(descricao)

    def clean_mensalidade(self):
        valor = self.cleaned_data.get("mensalidade")
        if valor is not None and valor < 0:
            raise forms.ValidationError(_("Valor inválido"))
        return valor


class NucleoSearchForm(forms.Form):
    q = forms.CharField(label="", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["q"].widget.attrs.setdefault("placeholder", _("Buscar..."))
        self.fields["q"].widget.attrs.setdefault("aria-label", _("Buscar núcleos"))


class ParticipacaoForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoNucleo
        fields = ["nucleo"]
        widgets = {"nucleo": forms.HiddenInput()}


class ParticipacaoDecisaoForm(forms.Form):
    acao = forms.CharField(widget=forms.HiddenInput())


class MembroRoleForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoNucleo
        fields = ["papel"]


class NucleoPortfolioFilterForm(forms.Form):
    q = forms.CharField(
        label=_("Buscar"),
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": _("Buscar por descrição ou tags...")}
        ),
    )


class NucleoMediaForm(forms.ModelForm):
    tags_field = forms.CharField(
        required=False,
        help_text=_("Separe as tags por vírgula"),
        label=_("Tags"),
    )

    class Meta:
        model = NucleoMidia
        fields = ("file", "descricao", "tags_field")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(
                self.instance.tags.values_list("nome", flat=True)
            )

    def save(self, commit: bool = True, *, nucleo: Nucleo | None = None) -> NucleoMidia:
        instance = super().save(commit=False)
        if nucleo is not None:
            instance.nucleo = nucleo
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
