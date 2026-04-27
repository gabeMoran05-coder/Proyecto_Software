from datetime import timedelta

from django.db import models
from django.utils import timezone

class Lote(models.Model):
    CADUCIDAD_VERDE = 'verde'
    CADUCIDAD_AMARILLO = 'amarillo'
    CADUCIDAD_ROJO = 'rojo'

    id_lote = models.AutoField(primary_key=True)
    id_prov = models.ForeignKey('proveedores.Proveedor', on_delete=models.CASCADE, db_column='id_prov')
    numero_lote = models.CharField(max_length=60)
    fecha_fabricacion = models.DateField(null=True, blank=True)
    fecha_caducidad = models.DateField(null=True, blank=True)
    fecha_ingreso = models.DateTimeField(default=timezone.now, null=True, blank=True)
    stock_actual = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_compra = models.DateField(null=True, blank=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    oculto_por_caducidad = models.BooleanField(default=False)

    class Meta:
        db_table = 'lote'

    def __str__(self):
        return self.numero_lote

    @property
    def dias_para_caducar(self):
        if not self.fecha_caducidad:
            return None
        return (self.fecha_caducidad - timezone.localdate()).days

    @property
    def estado_caducidad(self):
        if not self.fecha_caducidad:
            return self.CADUCIDAD_VERDE
        if self.fecha_caducidad < timezone.localdate():
            return self.CADUCIDAD_ROJO
        if self.fecha_caducidad <= timezone.localdate() + timedelta(days=90):
            return self.CADUCIDAD_AMARILLO
        return self.CADUCIDAD_VERDE

    def estado_caducidad_display(self):
        if self.estado_caducidad == self.CADUCIDAD_ROJO:
            return 'Caduco'
        if self.estado_caducidad == self.CADUCIDAD_AMARILLO:
            return 'Proximo a caducar'
        return 'Vigente'

    @property
    def estado_stock(self):
        if self.stock_actual <= 0:
            return 'sin_stock'
        if self.stock_actual <= 5:
            return 'rojo'
        if self.stock_actual <= 20:
            return 'amarillo'
        return 'verde'

    def save(self, *args, **kwargs):
        if not self.fecha_ingreso:
            self.fecha_ingreso = timezone.now()
        super().save(*args, **kwargs)
        Medicamento.objects.filter(id_lote=self).update(
            estado_colorimetria=self.estado_stock
        )


class Medicamento(models.Model):
    ESTADO_CHOICES = [
        ('verde', 'Verde'),
        ('amarillo', 'Amarillo'),
        ('rojo', 'Rojo'),
        ('sin_stock', 'Sin Stock'),
    ]

    id_med = models.AutoField(primary_key=True)
    id_lote = models.ForeignKey(Lote, on_delete=models.CASCADE, db_column='id_lote', null=True, blank=True)
    nombre = models.CharField(max_length=120)
    presentacion = models.CharField(max_length=80, null=True, blank=True)
    concentracion = models.CharField(max_length=60, null=True, blank=True)
    requiere_receta = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=timezone.now, null=True, blank=True)
    estado_colorimetria = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='sin_stock')

    class Meta:
        db_table = 'medicamento'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.fecha_registro:
            self.fecha_registro = timezone.now()
        if self.id_lote_id:
            self.estado_colorimetria = self.id_lote.estado_stock
        super().save(*args, **kwargs)


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
