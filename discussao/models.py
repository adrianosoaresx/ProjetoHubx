from django.conf import settings
from django.db import models
from django.utils.text import slugify
from model_utils.models import TimeStampedModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Create your models here.

class CategoriaDiscussao(TimeStampedModel):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    descricao = models.TextField(blank=True)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="categorias_discussao",
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="categorias_discussao",
    )
    evento = models.ForeignKey(
        "agenda.Evento",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="categorias_discussao",
    )
    icone = models.ImageField(
        upload_to="discussoes/icones/", null=True, blank=True
    )

    class Meta:
        unique_together = ("nome", "organizacao", "nucleo", "evento")
        ordering = ["nome"]
        verbose_name = "Categoria de Discussão"
        verbose_name_plural = "Categorias de Discussão"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class TopicoDiscussao(TimeStampedModel):
    categoria = models.ForeignKey(
        CategoriaDiscussao,
        on_delete=models.CASCADE,
        related_name="topicos",
    )
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    conteudo = models.TextField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topicos_discussao",
    )
    publico_alvo = models.PositiveSmallIntegerField(
        choices=[(0, "Todos"), (1, "Apenas nucleados"), (2, "Apenas associados")]
    )
    tags = models.CharField(max_length=255, blank=True)
    numero_visualizacoes = models.PositiveIntegerField(default=0)
    fechado = models.BooleanField(default=False)
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    evento = models.ForeignKey(
        "agenda.Evento",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["slug", "categoria"])]
        verbose_name = "Tópico de Discussão"
        verbose_name_plural = "Tópicos de Discussão"

    def incrementar_visualizacao(self):
        self.numero_visualizacoes += 1
        self.save()


class RespostaDiscussao(TimeStampedModel):
    topico = models.ForeignKey(
        TopicoDiscussao,
        on_delete=models.CASCADE,
        related_name="respostas",
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="respostas_discussao",
    )
    conteudo = models.TextField()
    arquivo = models.FileField(
        upload_to="discussoes/arquivos/", null=True, blank=True
    )
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="respostas_filhas",
    )
    editado = models.BooleanField(default=False)

    class Meta:
        ordering = ["created"]
        verbose_name = "Resposta de Discussão"
        verbose_name_plural = "Respostas de Discussão"

    def editar_resposta(self, novo_conteudo):
        self.conteudo = novo_conteudo
        self.editado = True
        self.save()


class InteracaoDiscussao(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    tipo = models.CharField(
        max_length=7,
        choices=[("like", "Curtir"), ("dislike", "Não Curtir")],
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "content_type", "object_id")
