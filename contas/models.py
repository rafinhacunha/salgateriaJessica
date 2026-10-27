from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema (classe Usuario do diagrama).

    login = username, nome = first_name, ativo = is_active, perfil = abaixo.
    A senha é guardada com hash pelo Django (nunca em texto puro).
    """

    class Perfil(models.TextChoices):
        PROPRIETARIA = "PROPRIETARIA", "Proprietária"
        ATENDENTE = "ATENDENTE", "Atendente"

    perfil = models.CharField(max_length=12, choices=Perfil.choices, default=Perfil.ATENDENTE)

    @property
    def eh_proprietaria(self):
        return self.perfil == self.Perfil.PROPRIETARIA

    @property
    def nome_exibicao(self):
        return self.first_name or self.username

    @property
    def iniciais(self):
        return self.nome_exibicao[:1].upper()

    def __str__(self):
        return self.nome_exibicao
