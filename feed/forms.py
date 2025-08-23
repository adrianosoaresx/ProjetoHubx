from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from feed.application.moderar_ai import aplicar_decisao, pre_analise


from accounts.models import UserType

from organizacoes.models import Organizacao

from .models import Comment, Like, Post, Tag
from .services import upload_media

User = get_user_model()


class PostForm(forms.ModelForm):
    """Formulário para criação e edição de ``Post``."""

    tipo_feed = forms.ChoiceField(choices=Post.TIPO_FEED_CHOICES)
    organizacao = forms.ModelChoiceField(queryset=None)

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
                    "class": "mt-1 block w-full rounded-xl border border-neutral-300 shadow-sm focus:ring-primary-500 focus:border-primary-500 text-sm",
                    "rows": 4,
                    "placeholder": "Compartilhe algo...",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "mt-2 block w-full text-sm text-neutral-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-neutral-100 file:text-neutral-700 hover:file:bg-neutral-200",
                }
            ),
            "pdf": forms.ClearableFileInput(
                attrs={
                    "class": "mt-2 block w-full text-sm text-neutral-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-neutral-100 file:text-neutral-700 hover:file:bg-neutral-200",
                }
            ),
            "video": forms.ClearableFileInput(
                attrs={
                    "class": "mt-2 block w-full text-sm text-neutral-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-neutral-100 file:text-neutral-700 hover:file:bg-neutral-200",
                }
            ),
        }

    def __init__(self, *args, user: User | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
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

    def clean(self):
        cleaned_data = super().clean()
        img = cleaned_data.get("image")
        pdf = cleaned_data.get("pdf")
        video = cleaned_data.get("video")
        conteudo = cleaned_data.get("conteudo")

        if sum(bool(x) for x in [img, pdf, video]) > 1:
            raise forms.ValidationError("Envie apenas uma mídia por vez.")
        if not conteudo and not img and not pdf and not video:
            raise forms.ValidationError("Informe um conteúdo ou selecione uma mídia.")

        for field in ["image", "pdf", "video"]:
            file = cleaned_data.get(field)
            if file and not isinstance(file, str):
                try:
                    result = upload_media(file)
                except ValidationError as e:
                    self.add_error(field, e.message)
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
        if (
            tipo_feed == "nucleo" and self.user and nucleo and nucleo not in self.user.nucleos.all()
        ):
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

        decision = pre_analise(conteudo or "")
        self._ai_decision = decision
        if decision == "rejeitado":
            raise forms.ValidationError("Conteúdo não permitido.")

        return cleaned_data

    def save(self, commit: bool = True):  # type: ignore[override]
        post = super().save(commit)
        if getattr(self, "_video_preview_key", None):
            post.video_preview = self._video_preview_key
            if commit:
                post.save(update_fields=["video_preview"])
        aplicar_decisao(post, getattr(self, "_ai_decision", "aceito"))
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
                    "class": "mt-1 block w-full rounded-xl border border-neutral-300 shadow-sm focus:ring-primary-500 focus:border-primary-500 text-sm",
                    "rows": 3,
                    "placeholder": "Escreva um comentário...",
                }
            ),
        }


class LikeForm(forms.ModelForm):
    class Meta:
        model = Like
        fields = ["post"]
        widgets = {"post": forms.HiddenInput()}


