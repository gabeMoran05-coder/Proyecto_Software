import secrets

from django.db import models # pyright: ignore[reportMissingModuleSource]
from django.core.validators import MinValueValidator


class MetodoPago(models.Model):
    id_metPag    = models.AutoField(primary_key=True)
    nombre_metodo = models.CharField(max_length=50, verbose_name='Método de pago')
    descripcion  = models.CharField(
        max_length=150, null=True, blank=True, verbose_name='Descripción'
    )

    class Meta:
        db_table            = 'metodo_pago'
        verbose_name        = 'Método de pago'
        verbose_name_plural = 'Métodos de pago'
        ordering            = ['nombre_metodo']

    def __str__(self):
        return self.nombre_metodo


class Venta(models.Model):
    id_ventas   = models.AutoField(primary_key=True)
    id_usuario  = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        db_column='id_usuario',
        verbose_name='Cajero',
    )
    id_metPag   = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        db_column='id_metPag',
        verbose_name='Método de pago',
    )
    id_cliente  = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='id_cliente',
        verbose_name='Cliente',
    )
    fecha_venta = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de venta'
    )
    total_venta = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='Total',
    )
    ticket_token = models.CharField(max_length=64, unique=True, null=True, blank=True)

    class Meta:
        db_table            = 'ventas'
        verbose_name        = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering            = ['-fecha_venta']

    def __str__(self):
        fecha = self.fecha_venta.strftime('%d/%m/%Y %H:%M') if self.fecha_venta else '—'
        return f'Venta #{self.id_ventas} — {fecha}'

    def num_productos(self):
        """Número de líneas de detalle de esta venta."""
        return self.detalleventa_set.count()

    def cliente_display(self):
        return str(self.id_cliente) if self.id_cliente else 'Público en general'


    def ensure_ticket_token(self):
        if self.ticket_token:
            return self.ticket_token

        token = secrets.token_urlsafe(32)
        while Venta.objects.filter(ticket_token=token).exclude(pk=self.pk).exists():
            token = secrets.token_urlsafe(32)

        self.ticket_token = token
        self.save(update_fields=['ticket_token'])
        return self.ticket_token


class DetalleVenta(models.Model):
    id_detalle      = models.AutoField(primary_key=True)
    id_ventas       = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        db_column='id_ventas',
        verbose_name='Venta',
    )
    id_medicamento  = models.ForeignKey(
        'medicamentos.Medicamento',
        on_delete=models.PROTECT,
        db_column='id_medicamento',
        verbose_name='Medicamento',
    )
    cantidad        = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='Cantidad',
    )
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='Precio unitario',
    )
    subtotal        = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='Subtotal',
    )

    class Meta:
        db_table            = 'detalle_ventas_medicamento'
        verbose_name        = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'
        ordering            = ['id_detalle']

    def __str__(self):
        return (
            f'{self.id_medicamento.nombre} × {self.cantidad} '
            f'— Venta #{self.id_ventas.id_ventas}'
        )

    def save(self, *args, **kwargs):
        """Calcula el subtotal automáticamente si no se proporcionó."""
        if self.cantidad and self.precio_unitario and not self.subtotal:
            self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
