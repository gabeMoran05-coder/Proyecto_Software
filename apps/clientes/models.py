from django.db import models
from django.utils import timezone

from apps.text_utils import first_upper, first_upper_or_none


class Cliente(models.Model):
    id_cliente     = models.AutoField(primary_key=True)
    nombre         = models.CharField(max_length=80, verbose_name='Nombre(s)')
    ap_pat         = models.CharField(
        max_length=60, null=True, blank=True, verbose_name='Apellido paterno'
    )
    ap_mat         = models.CharField(
        max_length=60, null=True, blank=True, verbose_name='Apellido materno'
    )
    fecha_registro = models.DateField(
        null=True, blank=True, verbose_name='Fecha de registro'
    )
    telefono       = models.CharField(
        max_length=15, null=True, blank=True, verbose_name='Teléfono'
    )

    class Meta:
        db_table         = 'cliente'
        verbose_name     = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering         = ['nombre', 'ap_pat']

    def __str__(self):
        partes = [self.nombre]
        if self.ap_pat:
            partes.append(self.ap_pat)
        if self.ap_mat:
            partes.append(self.ap_mat)
        return ' '.join(partes)

    def nombre_completo(self):
        """Retorna el nombre completo del cliente."""
        return str(self)

    def save(self, *args, **kwargs):
        self.nombre = first_upper(self.nombre)
        self.ap_pat = first_upper_or_none(self.ap_pat)
        self.ap_mat = first_upper_or_none(self.ap_mat)
        if not self.fecha_registro:
            self.fecha_registro = timezone.localdate()
        super().save(*args, **kwargs)

    def total_compras(self):
        """Total histórico de compras del cliente."""
        from django.db.models import Sum
        resultado = self.venta_set.aggregate(total=Sum('total_venta'))
        return resultado['total'] or 0
