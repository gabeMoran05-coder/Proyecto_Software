from django.db import models

class Lote(models.Model):
    id_lote = models.AutoField(primary_key=True)
    id_prov = models.ForeignKey('proveedores.Proveedor', on_delete=models.CASCADE, db_column='id_prov')
    numero_lote = models.CharField(max_length=60)
    fecha_fabricacion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField(null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    stock_actual = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_compra = models.DateField(null=True, blank=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'lote'

    def __str__(self):
        return self.numero_lote


class Medicamento(models.Model):
    ESTADO_CHOICES = [
        ('verde', 'Verde'),
        ('amarillo', 'Amarillo'),
        ('rojo', 'Rojo'),
        ('sin_stock', 'Sin Stock'),
    ]

    id_med = models.AutoField(primary_key=True)
    id_lote = models.ForeignKey(Lote, on_delete=models.CASCADE, db_column='id_lote')
    nombre = models.CharField(max_length=120)
    presentacion = models.CharField(max_length=80, null=True, blank=True)
    concentracion = models.CharField(max_length=60, null=True, blank=True)
    requiere_receta = models.BooleanField(default=False)
    fecha_registro = models.DateField(null=True, blank=True)
    estado_colorimetria = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='sin_stock')

    class Meta:
        db_table = 'medicamento'

    def __str__(self):
        return self.nombre


class CodigoQR(models.Model):
    id_qr = models.AutoField(primary_key=True)
    id_medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE, db_column='id_medicamento')
    token = models.CharField(max_length=64, unique=True)
    url_qr = models.CharField(max_length=255)
    fecha_generacion = models.DateField(null=True, blank=True)
    fecha_regeneracion = models.DateField(null=True, blank=True)
    contador_escaneos = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'codigos_qr'

    def __str__(self):
        return self.token