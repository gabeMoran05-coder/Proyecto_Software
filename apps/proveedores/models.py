from django.db import models

from apps.text_utils import first_upper, first_upper_or_none

class Proveedor(models.Model):
    id_prov = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    correo = models.CharField(max_length=100, null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'proveedor'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = first_upper(self.nombre)
        self.correo = self.correo.strip().lower() if self.correo else None
        self.direccion = first_upper_or_none(self.direccion)
        super().save(*args, **kwargs)
