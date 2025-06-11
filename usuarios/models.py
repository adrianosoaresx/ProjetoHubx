from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Usuario(AbstractUser):
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    data_nascimento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=1, blank=True)
    telefone = PhoneNumberField(blank=True)
    whatsapp = PhoneNumberField(blank=True)
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
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
