from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    rol = models.CharField(max_length=30)
    telefono = models.CharField(max_length=15, null=True, blank=True)

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.username