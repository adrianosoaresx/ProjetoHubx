from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):
    """Informações adicionais do usuário."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    data_nascimento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=1, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=10, blank=True)
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    website = models.URLField(blank=True)
    idioma = models.CharField(max_length=10, blank=True)
    fuso_horario = models.CharField(max_length=50, blank=True)
    perfil_publico = models.BooleanField(default=True)
    mostrar_email = models.BooleanField(default=True)
    mostrar_telefone = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"

    def __str__(self) -> str:  # pragma: no cover - simples
        return str(self.user)


class NotificationSettings(models.Model):
    """Preferências de notificação do usuário."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_settings")
    email_conexoes = models.BooleanField(default=True)
    email_mensagens = models.BooleanField(default=True)
    email_eventos = models.BooleanField(default=True)
    email_newsletter = models.BooleanField(default=True)
    sistema_conexoes = models.BooleanField(default=True)
    sistema_mensagens = models.BooleanField(default=True)
    sistema_eventos = models.BooleanField(default=True)
    sistema_comentarios = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuração de Notificação"
        verbose_name_plural = "Configurações de Notificação"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"Notificações de {self.user}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_e_notificacoes(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)
        NotificationSettings.objects.create(user=instance)
