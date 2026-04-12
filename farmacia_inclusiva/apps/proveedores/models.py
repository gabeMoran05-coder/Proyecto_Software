from django.db import models

class Proveedor(models.Model):
    nombre    = models.CharField('Nombre', max_length=200)
    telefono  = models.CharField('Teléfono', max_length=20, blank=True)
    correo    = models.EmailField('Correo', blank=True)
    direccion = models.TextField('Dirección', blank=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
