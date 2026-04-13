from django.db import models
from apps.usuarios.models import Usuario
from apps.clientes.models import Cliente

class MetodoPago(models.Model):
    id_metPag = models.AutoField(primary_key=True)
    nombre_metodo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        db_table = 'metodo_pago'

    def __str__(self):
        return self.nombre_metodo


class Venta(models.Model):
    id_ventas = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    id_metPag = models.ForeignKey(MetodoPago, on_delete=models.CASCADE, db_column='id_metPag')
    id_cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_cliente')
    fecha_venta = models.DateTimeField(null=True, blank=True)
    total_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'ventas'

    def __str__(self):
        return f'Venta {self.id_ventas}'


class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    id_ventas = models.ForeignKey(Venta, on_delete=models.CASCADE, db_column='id_ventas')
    id_medicamento = models.ForeignKey('medicamentos.Medicamento', on_delete=models.CASCADE, db_column='id_medicamento')
    cantidad = models.IntegerField(null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'detalle_ventas_medicamento'

    def __str__(self):
        return f'Detalle {self.id_detalle}'