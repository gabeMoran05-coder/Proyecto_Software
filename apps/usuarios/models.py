from django.db import models

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=60, unique=True)
    rol = models.CharField(max_length=30)
    fecha_creacion = models.DateField(null=True, blank=True)
    ultima_conexion = models.DateTimeField(null=True, blank=True)
    nombre = models.CharField(max_length=80)
    ap_pat = models.CharField(max_length=60, null=True, blank=True)
    ap_mat = models.CharField(max_length=60, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.usuario