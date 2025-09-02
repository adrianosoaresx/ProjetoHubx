from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.utils import timezone
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from core.models import SoftDeleteManager, SoftDeleteModel


class SearchVectorField(models.TextField):
    def db_type(self, connection):  # type: ignore[override]
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import SearchVectorField as PGSearchVectorField

            return PGSearchVectorField().db_type(connection)
        return "text"


# Create your models here.


class CategoriaDiscussao(TimeStampedModel, SoftDeleteModel):
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
    icone = models.ImageField(upload_to="discussoes/icones/", null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ("nome", "organizacao", "nucleo", "evento")
        ordering = ["nome"]
        verbose_name = "Categoria de Discussão"
        verbose_name_plural = "Categorias de Discussão"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class Tag(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome


class TopicoDiscussao(TimeStampedModel, SoftDeleteModel):
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
    melhor_resposta = models.ForeignKey(
        "RespostaDiscussao",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="topico_melhor_resposta",
    )
    tags = models.ManyToManyField("Tag", blank=True, related_name="topicos")
    fechado = models.BooleanField(default=False)
    resolvido = models.BooleanField(default=False)
    numero_visualizacoes = models.PositiveIntegerField(default=0)
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
    interacoes = GenericRelation("InteracaoDiscussao")
    search_vector = SearchVectorField(blank=True, null=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        if connection.vendor != "postgresql":
            self.search_vector = f"{self.titulo} {self.conteudo}"
        super().save(*args, **kwargs)
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import SearchVector

            type(self).objects.filter(pk=self.pk).update(
                search_vector=SearchVector("titulo", weight="A") + SearchVector("conteudo", weight="B")
            )

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["slug", "categoria"])]
        verbose_name = "Tópico de Discussão"
        verbose_name_plural = "Tópicos de Discussão"

    def incrementar_visualizacao(self):
        self.numero_visualizacoes += 1
        self.save()

    @property
    def score(self) -> int:
        return self.interacoes.aggregate(total=models.Sum("valor"))["total"] or 0

    @property
    def num_votos(self) -> int:
        return self.interacoes.count()


class RespostaDiscussao(TimeStampedModel, SoftDeleteModel):
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
    arquivo = models.FileField(upload_to="discussoes/arquivos/", null=True, blank=True)
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="respostas_filhas",
    )
    editado = models.BooleanField(default=False)
    editado_em = models.DateTimeField(null=True, blank=True)
    motivo_edicao = models.TextField(blank=True, default="")
    interacoes = GenericRelation("InteracaoDiscussao")
    search_vector = SearchVectorField(blank=True, null=True, editable=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["created"]
        verbose_name = "Resposta de Discussão"
        verbose_name_plural = "Respostas de Discussão"

    def editar_resposta(self, novo_conteudo):
        self.conteudo = novo_conteudo
        self.editado = True
        self.editado_em = timezone.now()
        self.save()

    def save(self, *args, **kwargs):  # type: ignore[override]
        if connection.vendor != "postgresql":
            self.search_vector = self.conteudo
        super().save(*args, **kwargs)
        if connection.vendor == "postgresql":
            from django.contrib.postgres.search import SearchVector

            type(self).objects.filter(pk=self.pk).update(
                search_vector=SearchVector("conteudo")
            )

    @property
    def score(self) -> int:
        return self.interacoes.aggregate(total=models.Sum("valor"))["total"] or 0

    @property
    def num_votos(self) -> int:
        return self.interacoes.count()


class InteracaoDiscussao(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    valor = models.SmallIntegerField(choices=[(1, "Curtir"), (-1, "Não Curtir")], default=1)

    class Meta:
        unique_together = ("user", "content_type", "object_id")

    @property
    def tipo(self) -> str:
        return "like" if self.valor == 1 else "dislike"

    @tipo.setter
    def tipo(self, value: str) -> None:
        self.valor = 1 if value == "like" else -1


class Denuncia(TimeStampedModel):
    """Denúncia de conteúdo para moderação."""

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        REVISADO = "revisado", "Revisado"
        REJEITADO = "rejeitado", "Rejeitado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    motivo = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDENTE
    )
    log = models.ForeignKey(
        "DiscussionModerationLog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="denuncias",
    )

    class Meta:
        unique_together = ("user", "content_type", "object_id")
        verbose_name = "Denúncia"
        verbose_name_plural = "Denúncias"

    def aprovar(self, moderator, notes: str = ""):
        log = DiscussionModerationLog.objects.create(
            content_object=self.content_object,
            action="approve",
            moderator=moderator,
            notes=notes,
        )
        self.status = self.Status.REVISADO
        self.log = log
        self.save(update_fields=["status", "log"])
        return log

    def rejeitar(self, moderator, notes: str = ""):
        log = DiscussionModerationLog.objects.create(
            content_object=self.content_object,
            action="reject",
            moderator=moderator,
            notes=notes,
        )
        self.status = self.Status.REJEITADO
        self.log = log
        self.save(update_fields=["status", "log"])
        return log


class DiscussionModerationLog(TimeStampedModel):
    ACTION_CHOICES = [
        ("approve", "Aprovar"),
        ("reject", "Rejeitar"),
        ("remove", "Remover"),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_moderations",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Log de Moderação"
        verbose_name_plural = "Logs de Moderação"
