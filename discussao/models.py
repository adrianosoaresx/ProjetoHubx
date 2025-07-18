from django.db import models
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

# Create your models here.

class CategoriaDiscussao(TimeStampedModel):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    descricao = models.TextField(blank=True)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao", on_delete=models.CASCADE
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo", on_delete=models.SET_NULL, null=True, blank=True
    )
    evento = models.ForeignKey(
        "agenda.Evento", on_delete=models.SET_NULL, null=True, blank=True
    )
    icone = models.ImageField(
        upload_to="discussoes/icones/", null=True, blank=True
    )

    class Meta:
        unique_together = ("nome", "organizacao", "nucleo", "evento")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class TopicoDiscussao(TimeStampedModel):
    categoria = models.ForeignKey(CategoriaDiscussao, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    conteudo = models.TextField()
    autor = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    publico_alvo = models.PositiveSmallIntegerField(
        choices=[(0, "Todos"), (1, "Apenas nucleados"), (2, "Apenas associados")]
    )
    tags = models.CharField(max_length=255, blank=True)
    numero_visualizacoes = models.PositiveIntegerField(default=0)
    fechado = models.BooleanField(default=False)
    nucleo = models.ForeignKey(
        "nucleos.Nucleo", on_delete=models.SET_NULL, null=True, blank=True
    )
    evento = models.ForeignKey(
        "agenda.Evento", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["slug", "categoria"])
        ]

    def incrementar_visualizacao(self):
        self.numero_visualizacoes += 1
        self.save()


class RespostaDiscussao(TimeStampedModel):
    topico = models.ForeignKey(TopicoDiscussao, on_delete=models.CASCADE)
    autor = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    conteudo = models.TextField()
    arquivo = models.FileField(
        upload_to="discussoes/arquivos/", null=True, blank=True
    )
    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )
    editado = models.BooleanField(default=False)

    class Meta:
        ordering = ["created"]

    def editar_resposta(self, novo_conteudo):
        self.conteudo = novo_conteudo
        self.editado = True
        self.save()


class InteracaoDiscussao(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    content_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    tipo = models.CharField(max_length=10, choices=[("like", "Like"), ("dislike", "Dislike")])

    class Meta:
        unique_together = ("user", "content_type", "object_id")
