from django.db import models

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=80)
    ap_pat = models.CharField(max_length=60, null=True, blank=True)
    ap_mat = models.CharField(max_length=60, null=True, blank=True)
    fecha_registro = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)

    class Meta:
        db_table = 'cliente'

    def __str__(self):
        return f'{self.nombre} {self.ap_pat}'