from decimal import Decimal

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ClearableFileInput
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_select2 import forms as s2forms
from nucleos.models import Nucleo

from accounts.models import MediaTag, UserType
from accounts.forms import ProfileImageFileInput

from .validators import validate_uploaded_file
from .models import (
    BriefingEvento,
    BriefingTemplate,
    Convite,
    Evento,
    EventoMidia,
    FeedbackNota,
    InscricaoEvento,
)


class PublicInviteEmailForm(forms.Form):
    email = forms.EmailField(label=_("Email"))


class ConviteEventoForm(forms.ModelForm):
    _evento_prefilled_fields = (
        "publico_alvo",
        "data_inicio",
        "data_fim",
        "local",
        "cidade",
        "estado",
        "cronograma",
        "informacoes_adicionais",
        "numero_participantes",
    )

    class Meta:
        model = Convite
        fields = [
            "publico_alvo",
            "data_inicio",
            "data_fim",
            "local",
            "cidade",
            "estado",
            "cronograma",
            "informacoes_adicionais",
            "numero_participantes",
            "imagem",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "cronograma": forms.Textarea,
            "informacoes_adicionais": forms.Textarea,
        }

    def __init__(self, *args, evento=None, **kwargs):
        initial = kwargs.setdefault("initial", {})

        if evento:
            initial.setdefault("publico_alvo", evento.get_publico_alvo_display())
            initial.setdefault("data_inicio", evento.data_inicio.date())
            initial.setdefault("data_fim", evento.data_fim.date())
            initial.setdefault("local", evento.local)
            initial.setdefault("cidade", evento.cidade)
            initial.setdefault("estado", evento.estado)
            initial.setdefault("cronograma", evento.cronograma)
            initial.setdefault("informacoes_adicionais", evento.informacoes_adicionais)
            initial.setdefault(
                "numero_participantes",
                evento.participantes_maximo or evento.numero_presentes or None,
            )

        super().__init__(*args, **kwargs)

        for field_name in self._evento_prefilled_fields:
            if field_name in self.fields:
                field = self.fields[field_name]
                field.disabled = True
                field.widget.attrs["aria-disabled"] = "true"

        self.fields["imagem"].widget.attrs.setdefault("data-convite-image-input", "true")


class PDFClearableFileInput(ClearableFileInput):
    template_name = "eventos/widgets/pdf_clearable_file_input.html"

    def __init__(self, attrs=None, *, button_label=None, empty_label=None):
        self.button_label = button_label or _("Enviar PDF")
        self.empty_label = empty_label or _("Nenhum arquivo selecionado")
        attrs = (attrs or {}).copy()
        existing_classes = attrs.get("class", "").split()
        if "sr-only" not in existing_classes:
            existing_classes.append("sr-only")
        attrs["class"] = " ".join(filter(None, existing_classes))
        attrs.setdefault("data-file-upload-input", "true")
        attrs.setdefault("data-empty-text", self.empty_label)
        super().__init__(attrs=attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        widget["button_label"] = self.button_label
        widget["empty_label"] = self.empty_label
        final_attrs = widget.get("attrs", {})
        final_attrs.setdefault("data-file-upload-input", "true")
        final_attrs.setdefault("data-empty-text", self.empty_label)
        widget["attrs"] = final_attrs

        value_name = ""
        if value:
            if hasattr(value, "name"):
                value_name = value.name or ""
            else:
                value_name = str(value)
        widget["value_name"] = value_name
        return context


class ComprovanteFileInput(ClearableFileInput):
    template_name = "eventos/widgets/comprovante_file_input.html"

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        existing_classes = attrs.get("class", "")
        attrs["class"] = f"{existing_classes} sr-only".strip()
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        attrs = (attrs or {}).copy()
        existing_classes = attrs.get("class", "")
        if "sr-only" not in existing_classes.split():
            attrs["class"] = f"{existing_classes} sr-only".strip()
        attrs["data-payment-proof-input"] = "true"
        context = super().get_context(name, value, attrs)
        initial_name = ""
        initial_url = ""
        if value:
            if hasattr(value, "name"):
                initial_name = value.name or ""
            else:
                initial_name = str(value)
            if hasattr(value, "url"):
                initial_url = getattr(value, "url", "") or ""
        context["widget"]["initial_name"] = initial_name
        context["widget"]["initial_url"] = initial_url
        return context


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            "titulo",
            "descricao",
            "data_inicio",
            "data_fim",
            "local",
            "cidade",
            "estado",
            "cep",
            "status",
            "publico_alvo",
            "nucleo",
            "participantes_maximo",
            "gratuito",
            "valor_associado",
            "valor_nucleado",
            "cronograma",
            "informacoes_adicionais",
            "avatar",
            "cover",
        ]
        widgets = {
            "data_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "descricao": forms.Textarea(attrs={"rows": 10}),
            "avatar": ProfileImageFileInput(
                button_label=_("Enviar foto"),
                empty_label=_("Nenhuma foto selecionada"),
            ),
            "cover": ProfileImageFileInput(
                button_label=_("Enviar imagem"),
                empty_label=_("Nenhuma imagem selecionada"),
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if not self.is_bound:
            for field_name in ("data_inicio", "data_fim"):
                dt_value = getattr(self.instance, field_name, None)
                if dt_value:
                    if timezone.is_naive(dt_value):
                        local_dt = timezone.make_naive(dt_value, timezone.get_current_timezone())
                    else:
                        local_dt = timezone.localtime(dt_value)
                    self.initial[field_name] = local_dt.strftime("%Y-%m-%dT%H:%M")

        nucleo_field = self.fields.get("nucleo")
        if nucleo_field:
            nucleo_field.required = False
            nucleo_field.empty_label = _("Selecione um núcleo")

            queryset = Nucleo.objects.none()
            organizacao = None

            if self.request:
                try:
                    organizacao = getattr(self.request.user, "organizacao", None)
                except ObjectDoesNotExist:
                    organizacao = None

            if not organizacao and self.instance and getattr(self.instance, "organizacao_id", None):
                organizacao = self.instance.organizacao

            if organizacao:
                queryset = Nucleo.objects.filter(organizacao=organizacao).order_by("nome")

            if self._is_coordenador(self.request):
                usuario_nucleo_id = getattr(self.request.user, "nucleo_id", None)
                if usuario_nucleo_id:
                    queryset = Nucleo.objects.filter(pk=usuario_nucleo_id)
                    if not self.is_bound and not getattr(self.instance, "nucleo_id", None):
                        self.initial["nucleo"] = usuario_nucleo_id
                else:
                    queryset = Nucleo.objects.none()
                nucleo_field.empty_label = None

            if self.instance and self.instance.nucleo:
                queryset = queryset | Nucleo.objects.filter(pk=self.instance.nucleo.pk)

            nucleo_field.queryset = queryset.distinct()

        if "avatar" in self.fields:
            self.fields["avatar"].label = _("Foto do perfil")

        if "cover" in self.fields:
            self.fields["cover"].label = _("Imagem da capa")

        participantes_field = self.fields.get("participantes_maximo")
        if participantes_field:
            participantes_field.label = _("Participantes (lotação)")

    def clean(self):
        cleaned_data = super().clean()
        publico_alvo = cleaned_data.get("publico_alvo")
        nucleo = cleaned_data.get("nucleo")

        if publico_alvo == 1:
            if not nucleo:
                self.add_error("nucleo", _("Selecione um núcleo para eventos destinados apenas ao núcleo."))
        else:
            cleaned_data["nucleo"] = None

        if self._is_coordenador(self.request):
            nucleo = cleaned_data.get("nucleo")
            usuario_nucleo_id = getattr(self.request.user, "nucleo_id", None)
            nucleo_id = nucleo.pk if nucleo else None
            if nucleo_id != usuario_nucleo_id:
                self.add_error(
                    "nucleo",
                    _("Coordenadores só podem criar eventos do próprio núcleo."),
                )

        participantes_maximo = cleaned_data.get("participantes_maximo")

        if cleaned_data.get("gratuito"):
            cleaned_data["valor_associado"] = Decimal("0.00")
            cleaned_data["valor_nucleado"] = Decimal("0.00")

        return cleaned_data

    @staticmethod
    def _is_coordenador(request) -> bool:
        if not request or not getattr(request, "user", None):
            return False
        tipo = getattr(request.user, "get_tipo_usuario", None)
        if isinstance(tipo, UserType):
            tipo = tipo.value
        elif hasattr(tipo, "value"):
            tipo = tipo.value
        return tipo == UserType.COORDENADOR.value


def _apply_design_system_classes(field: forms.Field) -> None:
    widget = field.widget
    attrs = widget.attrs.copy()
    existing_classes = attrs.get("class", "").split()
    for class_name in ("form-field", "card"):
        if class_name not in existing_classes:
            existing_classes.append(class_name)
    attrs["class"] = " ".join(filter(None, existing_classes))
    widget.attrs = attrs


class BriefingTemplateForm(forms.ModelForm):
    class Meta:
        model = BriefingTemplate
        fields = ["nome", "descricao", "estrutura", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "estrutura": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_design_system_classes(field)

    def clean_estrutura(self):
        estrutura = self.cleaned_data.get("estrutura")
        if not isinstance(estrutura, list):
            raise forms.ValidationError(
                _("A estrutura deve ser uma lista de perguntas.")
            )

        tipos_permitidos = {"text", "textarea", "number", "email", "date", "select", "boolean"}
        for index, pergunta in enumerate(estrutura, start=1):
            if not isinstance(pergunta, dict):
                raise forms.ValidationError(
                    _("A pergunta %(numero)s deve ser um objeto JSON válido.")
                    % {"numero": index}
                )
            for campo in ("label", "type", "required"):
                if campo not in pergunta:
                    raise forms.ValidationError(
                        _("Cada pergunta deve conter 'label', 'type' e 'required'.")
                    )
            label = pergunta.get("label")
            tipo = pergunta.get("type")
            required = pergunta.get("required")
            if not isinstance(label, str) or not label.strip():
                raise forms.ValidationError(
                    _("A pergunta %(numero)s precisa de um rótulo válido.")
                    % {"numero": index}
                )
            if not isinstance(tipo, str) or tipo not in tipos_permitidos:
                raise forms.ValidationError(
                    _("Tipo de pergunta inválido em %(numero)s.")
                    % {"numero": index}
                )
            if not isinstance(required, bool):
                raise forms.ValidationError(
                    _("O campo 'required' da pergunta %(numero)s deve ser booleano.")
                    % {"numero": index}
                )
            if tipo == "select":
                opcoes = pergunta.get("options") or pergunta.get("choices")
                if not isinstance(opcoes, list) or not opcoes:
                    raise forms.ValidationError(
                        _("A pergunta %(numero)s do tipo select precisa de opções.")
                        % {"numero": index}
                    )
        return estrutura


class BriefingEventoForm(forms.ModelForm):
    class Meta:
        model = BriefingEvento
        fields = []

    def __init__(self, *args, template: BriefingTemplate | None = None, **kwargs):
        self.template = template
        super().__init__(*args, **kwargs)
        if self.template is None:
            self.template = getattr(self.instance, "template", None)

        self._perguntas: list[dict[str, str]] = []
        respostas_iniciais = getattr(self.instance, "respostas", {}) or {}
        estrutura = getattr(self.template, "estrutura", []) if self.template else []

        if isinstance(estrutura, list):
            for index, pergunta in enumerate(estrutura, start=1):
                if not isinstance(pergunta, dict):
                    continue
                label = pergunta.get("label") or _("Pergunta %(numero)s") % {"numero": index}
                tipo = pergunta.get("type") or "text"
                required = bool(pergunta.get("required"))
                field_name = f"pergunta_{index}"
                field = self._build_pergunta_field(pergunta, label, tipo, required)
                self.fields[field_name] = field
                self._perguntas.append({"field": field_name, "label": label})
                if label in respostas_iniciais:
                    self.initial[field_name] = respostas_iniciais.get(label)

        for field in self.fields.values():
            _apply_design_system_classes(field)

    def _build_pergunta_field(
        self, pergunta: dict, label: str, tipo: str, required: bool
    ) -> forms.Field:
        error_messages = {"required": _("Campo obrigatório.")}
        if tipo == "textarea":
            return forms.CharField(
                label=label,
                required=required,
                widget=forms.Textarea(attrs={"rows": 4}),
                error_messages=error_messages,
            )
        if tipo == "number":
            return forms.DecimalField(
                label=label,
                required=required,
                error_messages=error_messages,
            )
        if tipo == "email":
            return forms.EmailField(
                label=label,
                required=required,
                error_messages=error_messages,
            )
        if tipo == "date":
            return forms.DateField(
                label=label,
                required=required,
                widget=forms.DateInput(attrs={"type": "date"}),
                error_messages=error_messages,
            )
        if tipo == "select":
            opcoes = pergunta.get("options") or pergunta.get("choices") or []
            choices: list[tuple[str, str]] = []
            for opcao in opcoes:
                if isinstance(opcao, dict):
                    valor = str(opcao.get("value") or opcao.get("id") or opcao.get("label") or "")
                    rotulo = str(opcao.get("label") or opcao.get("value") or opcao.get("id") or "")
                else:
                    valor = str(opcao)
                    rotulo = str(opcao)
                if valor:
                    choices.append((valor, rotulo))
            return forms.ChoiceField(
                label=label,
                required=required,
                choices=choices,
                error_messages={**error_messages, "invalid_choice": _("Selecione uma opção válida.")},
            )
        if tipo == "boolean":
            return forms.BooleanField(
                label=label,
                required=required,
                error_messages=error_messages,
            )
        return forms.CharField(
            label=label,
            required=required,
            error_messages=error_messages,
        )

    def clean(self):
        cleaned_data = super().clean()
        respostas: dict[str, object] = {}
        for pergunta in self._perguntas:
            field_name = pergunta["field"]
            label = pergunta["label"]
            respostas[label] = cleaned_data.get(field_name)
        cleaned_data["respostas"] = respostas
        return cleaned_data

    def save(self, commit: bool = True) -> BriefingEvento:
        instance = super().save(commit=False)
        instance.respostas = self.cleaned_data.get("respostas", {})
        if self.template is not None:
            instance.template = self.template
        if commit:
            instance.save()
        return instance


class EventoWidget(s2forms.ModelSelect2Widget):
    search_fields = ["titulo__icontains"]


class EventoSearchForm(forms.Form):
    evento = forms.ModelChoiceField(
        queryset=Evento.objects.all(),
        required=False,
        label="",
        widget=EventoWidget(
            attrs={
                "data-placeholder": "Buscar eventos...",
                "data-minimum-input-length": 2,
            }
        ),
    )


class InscricaoEventoForm(forms.ModelForm):
    def __init__(self, *args, evento=None, user=None, **kwargs):
        self.evento = evento
        self.user = user
        super().__init__(*args, **kwargs)

        if self.evento is None and self.instance and getattr(
            self.instance, "evento", None
        ) is not None:
            self.evento = self.instance.evento
        if self.user is None and self.instance and getattr(self.instance, "user", None):
            self.user = self.instance.user
        valor_field = self.fields.get("valor_pago")
        if valor_field:
            valor_inicial = self._get_evento_valor()
            if valor_inicial is None and self.instance and self.instance.valor_pago is not None:
                valor_inicial = self.instance.valor_pago
            if valor_inicial is not None:
                valor_field.initial = valor_inicial
            valor_field.disabled = True
            valor_field.widget.attrs.setdefault("readonly", "readonly")
            valor_field.label = _("Valor da inscrição")

        comprovante_field = self.fields.get("comprovante_pagamento")
        if comprovante_field:
            comprovante_field.label = _("Comprovante do pagamento")

        metodo_field = self.fields.get("metodo_pagamento")
        if metodo_field:
            metodo_field.required = not self._is_evento_gratuito()
            metodo_field.label = _("Metodos de pagamento")

    def _resolve_evento(self):
        if self.evento is not None:
            return self.evento
        if self.instance and getattr(self.instance, "evento", None) is not None:
            return self.instance.evento
        return None

    def _resolve_user(self):
        if self.user is not None:
            return self.user
        if self.instance and getattr(self.instance, "user", None) is not None:
            return self.instance.user
        return None

    def _get_evento_valor(self):
        evento = self._resolve_evento()
        if evento is None:
            return None
        return evento.get_valor_para_usuario(user=self._resolve_user())

    class Meta:
        model = InscricaoEvento
        fields = [
            "valor_pago",
            "metodo_pagamento",
            "comprovante_pagamento",
        ]
        widgets = {
            "comprovante_pagamento": ComprovanteFileInput(
                attrs={"accept": ".jpg,.jpeg,.png,.pdf"}
            ),
        }

    def _is_evento_gratuito(self):
        evento = self._resolve_evento()
        if evento is None:
            return False
        if getattr(evento, "gratuito", False):
            return True
        valor = evento.get_valor_para_usuario(user=self._resolve_user())
        if valor is None:
            return False
        return Decimal(valor) == Decimal("0.00")

    def clean_valor_pago(self):
        valor_evento = self._get_evento_valor()
        if valor_evento is not None:
            valor = valor_evento
        else:
            valor = self.cleaned_data.get("valor_pago")
        if valor is None:
            return valor
        if valor < 0:
            raise forms.ValidationError(_("O valor pago deve ser positivo."))
        if valor == 0 and not self._is_evento_gratuito():
            raise forms.ValidationError(_("O valor pago deve ser positivo."))
        return valor

    def clean_comprovante_pagamento(self):
        arquivo = self.cleaned_data.get("comprovante_pagamento")
        if not arquivo:
            return arquivo
        validate_uploaded_file(arquivo)
        return arquivo

    def clean_metodo_pagamento(self):
        metodo = self.cleaned_data.get("metodo_pagamento")
        if not metodo:
            instance_metodo = getattr(self.instance, "metodo_pagamento", None)
            transacao_metodo = getattr(getattr(self.instance, "transacao", None), "metodo", None)

            if instance_metodo:
                metodo = instance_metodo
            elif transacao_metodo:
                metodo = transacao_metodo

            if metodo:
                self.cleaned_data["metodo_pagamento"] = metodo
        if not self._is_evento_gratuito() and not metodo:
            raise forms.ValidationError(_("Selecione uma forma de pagamento."))
        return metodo


class FeedbackForm(forms.ModelForm):
    nota = forms.TypedChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        coerce=int,
        empty_value=None,
        label=_("Nota"),
    )

    class Meta:
        model = FeedbackNota
        fields = ["nota", "comentario"]
        widgets = {
            "comentario": forms.Textarea(attrs={"rows": 4}),
        }


class EventoPortfolioFilterForm(forms.Form):
    q = forms.CharField(
        label=_("Buscar"),
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": _("Buscar por descrição ou tags...")}
        ),
    )


class EventoMediaForm(forms.ModelForm):
    tags_field = forms.CharField(
        required=False,
        help_text="Separe as tags por vírgula",
        label="Tags",
    )

    class Meta:
        model = EventoMidia
        fields = ("file", "descricao", "tags_field")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags_field"].initial = ", ".join(
                self.instance.tags.values_list("nome", flat=True)
            )

    def save(self, commit: bool = True, *, evento: Evento | None = None) -> EventoMidia:
        instance = super().save(commit=False)
        if evento is not None:
            instance.evento = evento
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
