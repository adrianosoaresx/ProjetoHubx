from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import UserType

# Moderação desativada: sem análise por IA
from organizacoes.models import Organizacao

from .models import Comment, Post, Tag
from .services import upload_media

User = get_user_model()


class PostForm(forms.ModelForm):
    """Formulário para criação e edição de ``Post``."""

    tipo_feed = forms.ChoiceField(choices=Post.TIPO_FEED_CHOICES)
    organizacao = forms.ModelChoiceField(queryset=None)
    arquivo = forms.FileField(
        label=_("Arquivo"),
        help_text=_("Aceita imagem, PDF ou vídeo."),
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "tipo_feed",
            "organizacao",
            "conteudo",
            "image",
            "pdf",
            "video",
            "nucleo",
            "evento",
            "tags",
        ]
        widgets = {
            "conteudo": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full rounded-xl border border-[var(--border-secondary)] card-sm focus:ring-primary-500 focus:border-primary-500 text-sm",
                    "rows": 4,
                    "placeholder": "Compartilhe algo...",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                }
            ),
            "pdf": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                }
            ),
            "video": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                }
            ),
        }

    def __init__(self, *args, user: User | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        file_input_classes = (
            "mt-2 block w-full text-sm text-[var(--text-tertiary)] file:mr-4 file:py-2 "
            "file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold "
            "file:bg-[var(--bg-tertiary)] file:text-[var(--text-secondary)] hover:file:bg-[var(--bg-tertiary)]"
        )
        self.fields["arquivo"].widget = forms.ClearableFileInput(
            attrs={
                "class": file_input_classes,
                "accept": "image/*,application/pdf,video/*,.pdf",
            }
        )
        for field in ["image", "pdf", "video"]:
            self.fields[field].widget.attrs.update({"class": "hidden"})
            self.fields[field].required = False
        allowed_choices = [
            ("global", _("Público")),
            ("usuario", _("Privado")),
        ]
        current_value = self.data.get("tipo_feed") or getattr(self.instance, "tipo_feed", None)
        choice_map = dict(Post.TIPO_FEED_CHOICES)
        if current_value and current_value not in {value for value, _ in allowed_choices}:
            allowed_choices.append((current_value, choice_map.get(current_value, current_value)))
        self.fields["tipo_feed"].choices = allowed_choices
        if user:
            self.user = user
            self.fields["organizacao"].queryset = Organizacao.objects.filter(users=user)
            self.initial.setdefault("organizacao", getattr(user, "organizacao", None))
            self.fields["nucleo"].queryset = user.nucleos.all()
            if hasattr(user, "eventos"):
                self.fields["evento"].queryset = user.eventos.all()
            else:
                self.fields["evento"].queryset = self.fields["evento"].queryset.none()
            if user.user_type in {UserType.ROOT, UserType.ADMIN}:
                self.fields["organizacao"].queryset = Organizacao.objects.all()
            else:
                org = getattr(user, "organizacao", None)
                self.fields["organizacao"].queryset = (
                    Organizacao.objects.filter(pk=org.pk) if org else Organizacao.objects.none()
                )
        else:
            self.user = None

            self.fields["evento"].queryset = self.fields["evento"].queryset.none()
            self.fields["organizacao"].queryset = Organizacao.objects.none()
        self.fields["organizacao"].required = False

        self.fields["tags"].queryset = Tag.objects.all()
        self._video_preview_key: str | None = None
        self._arquivo_target: str | None = None

    def clean(self):
        cleaned_data = super().clean()
        arquivo = cleaned_data.get("arquivo")
        media_fields = ["image", "pdf", "video"]
        self._arquivo_target = None
        if arquivo and not isinstance(arquivo, str):
            content_type = getattr(arquivo, "content_type", "") or ""
            name = getattr(arquivo, "name", "") or ""
            lower_name = name.lower()
            if content_type == "application/pdf" or lower_name.endswith(".pdf"):
                target_field = "pdf"
            elif content_type.startswith("video/"):
                target_field = "video"
            else:
                target_field = "image"
            cleaned_data[target_field] = arquivo
            for field in media_fields:
                if field != target_field:
                    cleaned_data[field] = None
            self._arquivo_target = target_field
        cleaned_data["arquivo"] = arquivo

        img = cleaned_data.get("image")
        pdf = cleaned_data.get("pdf")
        video = cleaned_data.get("video")
        conteudo = cleaned_data.get("conteudo")

        if sum(bool(x) for x in [img, pdf, video]) > 1:
            raise forms.ValidationError("Envie apenas uma mídia por vez.")
        if not conteudo and not img and not pdf and not video:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma mídia.")

        for field in media_fields:
            file = cleaned_data.get(field)
            if file and not isinstance(file, str):
                try:
                    result = upload_media(file)
                except ValidationError as e:
                    if self._arquivo_target == field:
                        self.add_error("arquivo", e.message)
                    else:
                        self.add_error(field, e.message)
                    cleaned_data[field] = None
                    continue
                if field == "video" and isinstance(result, tuple):
                    cleaned_data[field] = result[0]
                    self._video_preview_key = result[1]
                else:
                    cleaned_data[field] = result
            elif isinstance(file, str):
                cleaned_data[field] = file

        tipo_feed = cleaned_data.get("tipo_feed")
        nucleo = cleaned_data.get("nucleo")
        evento = cleaned_data.get("evento")
        organizacao = cleaned_data.get("organizacao")

        if tipo_feed == "nucleo" and not nucleo:
            self.add_error("nucleo", "Selecione o núcleo.")
        if tipo_feed == "nucleo" and self.user and nucleo and nucleo not in self.user.nucleos.all():
            self.add_error("nucleo", "Usuário não é membro do núcleo.")
        if tipo_feed == "evento" and not evento:
            self.add_error("evento", "Selecione o evento.")

        if not organizacao:
            if self.instance.pk:
                self.add_error("organizacao", "Selecione a organização.")
            elif self.user:
                cleaned_data["organizacao"] = getattr(self.user, "organizacao", None)
        elif (
            self.user
            and self.user.user_type not in {UserType.ROOT, UserType.ADMIN}
            and organizacao != getattr(self.user, "organizacao", None)
        ):
            self.add_error("organizacao", "Usuário não pertence à organização.")

        # Moderação desativada: nenhuma análise de conteúdo
        self._ai_decision = "aceito"
        return cleaned_data

    def save(self, commit: bool = True):  # type: ignore[override]
        post = super().save(commit)
        if getattr(self, "_video_preview_key", None):
            post.video_preview = self._video_preview_key
            if commit:
                post.save(update_fields=["video_preview"])
        # Moderação desativada: nenhuma aplicação de decisão
        return post


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["post", "texto", "reply_to"]
        widgets = {
            "post": forms.HiddenInput(),
            "reply_to": forms.HiddenInput(),
            "texto": forms.Textarea(
                attrs={
                    "class": "mt-1 block w-full rounded-xl border border-[var(--border-secondary)] card-sm focus:ring-primary-500 focus:border-primary-500 text-sm",
                    "rows": 3,
                    "placeholder": "Escreva um comentário...",
                }
            ),
        }
