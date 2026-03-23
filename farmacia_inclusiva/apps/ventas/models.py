from django.db import models
from django.conf import settings


class Cliente(models.Model):
    nombre         = models.CharField('Nombre', max_length=100)
    ap_pat         = models.CharField('Apellido paterno', max_length=100)
    ap_mat         = models.CharField('Apellido materno', max_length=100, blank=True)
    telefono       = models.CharField('Teléfono / WhatsApp', max_length=20, blank=True)
    fecha_registro = models.DateTimeField('Fecha de registro', auto_now_add=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['ap_pat', 'nombre']

    def __str__(self):
        return f"{self.nombre} {self.ap_pat}"

    def nombre_completo(self):
        return f"{self.nombre} {self.ap_pat} {self.ap_mat}".strip()


class MetodoPago(models.Model):
    nombre      = models.CharField('Método', max_length=50, unique=True)
    descripcion = models.CharField('Descripción', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Método de pago'
        verbose_name_plural = 'Métodos de pago'

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    usuario     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='ventas'
    )
    cliente     = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ventas'
    )
    metodo_pago = models.ForeignKey(
        MetodoPago, on_delete=models.SET_NULL,
        null=True, related_name='ventas'
    )
    fecha_venta = models.DateTimeField('Fecha de venta', auto_now_add=True)
    total_venta = models.DecimalField('Total', max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"Venta #{self.pk} – {self.fecha_venta.strftime('%d/%m/%Y %H:%M')}"

    def calcular_total(self):
        total = sum(d.subtotal for d in self.detalles.all())
        self.total_venta = total
        self.save(update_fields=['total_venta'])


class DetalleVenta(models.Model):
    venta           = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    medicamento     = models.ForeignKey('medicamentos.Medicamento', on_delete=models.PROTECT)
    lote            = models.ForeignKey('medicamentos.Lote', on_delete=models.PROTECT, null=True, blank=True)
    cantidad        = models.PositiveIntegerField('Cantidad')
    precio_unitario = models.DecimalField('Precio unitario', max_digits=10, decimal_places=2)
    subtotal        = models.DecimalField('Subtotal', max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
        if self.lote:
            self.lote.stock_actual = max(0, self.lote.stock_actual - self.cantidad)
            self.lote.save(update_fields=['stock_actual'])

    def __str__(self):
        return f"{self.cantidad}x {self.medicamento.nombre}"
