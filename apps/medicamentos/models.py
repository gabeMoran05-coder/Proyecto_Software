from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.text_utils import first_upper, first_upper_or_none, upper_code

class Lote(models.Model):
    CADUCIDAD_VERDE = 'verde'
    CADUCIDAD_AMARILLO = 'amarillo'
    CADUCIDAD_ROJO = 'rojo'
    MOTIVO_CADUCIDAD = 'caducidad'
    MOTIVO_DEFECTUOSO = 'defectuoso'
    MOTIVO_DANINO = 'danino'
    MOTIVO_MERMA = 'merma'
    MOTIVO_ROBO = 'robo'
    MOTIVO_CORRECCION = 'correccion'
    MOTIVO_DEVOLUCION = 'devolucion'
    MOTIVO_INACTIVO = 'inactivo'

    MOTIVO_OCULTAR_CHOICES = [
        (MOTIVO_CADUCIDAD, 'Caducidad'),
        (MOTIVO_DEFECTUOSO, 'Defectuoso'),
        (MOTIVO_DANINO, 'Dañino o riesgoso'),
        (MOTIVO_MERMA, 'Merma'),
        (MOTIVO_ROBO, 'Robo'),
        (MOTIVO_CORRECCION, 'Correccion'),
        (MOTIVO_DEVOLUCION, 'Devolucion'),
        (MOTIVO_INACTIVO, 'Inactivo'),
    ]

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
    motivo_oculto = models.CharField(max_length=30, choices=MOTIVO_OCULTAR_CHOICES, blank=True)
    detalle_oculto = models.TextField(blank=True)
    fecha_oculto = models.DateTimeField(null=True, blank=True)

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
        if self.fecha_caducidad <= timezone.localdate():
            return self.CADUCIDAD_ROJO
        if self.fecha_caducidad <= timezone.localdate() + timedelta(days=self.dias_alerta_caducidad):
            return self.CADUCIDAD_AMARILLO
        return self.CADUCIDAD_VERDE

    @property
    def dias_alerta_caducidad(self):
        if not self.pk:
            return 90
        medicamentos = list(self.medicamento_set.all())
        valores = [med.dias_alerta_caducidad for med in medicamentos if med.dias_alerta_caducidad is not None]
        return max(valores) if valores else 90

    def estado_caducidad_display(self):
        if self.estado_caducidad == self.CADUCIDAD_ROJO:
            return 'Caduco'
        if self.estado_caducidad == self.CADUCIDAD_AMARILLO:
            return 'Próximo a caducar'
        return 'Vigente'

    @property
    def estado_stock(self):
        if self.stock_actual <= 0:
            return 'sin_stock'
        if self.stock_actual < 50:
            return 'amarillo'
        return 'verde'

    def save(self, *args, **kwargs):
        self.numero_lote = upper_code(self.numero_lote)
        if not self.fecha_ingreso:
            self.fecha_ingreso = timezone.now()
        if self.oculto_por_caducidad:
            self.activo = False
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'activo'}
        if not self.activo:
            self.oculto_por_caducidad = True
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'oculto_por_caducidad'}
            if not self.motivo_oculto:
                self.motivo_oculto = self.MOTIVO_CADUCIDAD if self.estado_caducidad == self.CADUCIDAD_ROJO else self.MOTIVO_INACTIVO
            if not self.fecha_oculto:
                self.fecha_oculto = timezone.now()
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
    tamano_presentacion = models.CharField(max_length=80, null=True, blank=True)
    concentracion = models.CharField(max_length=60, null=True, blank=True)
    requiere_receta = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=timezone.now, null=True, blank=True)
    estado_colorimetria = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='sin_stock')
    stock_minimo = models.PositiveIntegerField(default=50)
    dias_alerta_caducidad = models.PositiveSmallIntegerField(default=90)

    class Meta:
        db_table = 'medicamento'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = first_upper(self.nombre)
        self.presentacion = first_upper_or_none(self.presentacion)
        self.tamano_presentacion = first_upper_or_none(self.tamano_presentacion)
        self.concentracion = first_upper_or_none(self.concentracion)
        if not self.fecha_registro:
            self.fecha_registro = timezone.now()
        if self.id_lote_id:
            self.estado_colorimetria = self.id_lote.estado_stock
        super().save(*args, **kwargs)

    @property
    def presentacion_completa(self):
        partes = [self.presentacion, self.tamano_presentacion]
        return ' '.join(part for part in partes if part)


class MovimientoInventario(models.Model):
    TIPO_ENTRADA = 'entrada'
    TIPO_SALIDA = 'salida'
    TIPO_AJUSTE = 'ajuste'
    TIPO_VENTA = 'venta'
    TIPO_CANCELACION = 'cancelacion'
    TIPO_CONTEO = 'conteo'
    TIPO_OCULTAMIENTO = 'ocultamiento'

    TIPO_CHOICES = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SALIDA, 'Salida'),
        (TIPO_AJUSTE, 'Ajuste'),
        (TIPO_VENTA, 'Venta'),
        (TIPO_CANCELACION, 'Cancelación'),
        (TIPO_CONTEO, 'Conteo físico'),
        (TIPO_OCULTAMIENTO, 'Ocultamiento'),
    ]

    MOTIVO_CHOICES = [
        ('compra', 'Compra'),
        ('venta', 'Venta'),
        ('cancelacion', 'Cancelación'),
        ('merma', 'Merma'),
        ('robo', 'Robo'),
        ('defectuoso', 'Defectuoso'),
        ('danino', 'Dañino o riesgoso'),
        ('correccion', 'Corrección'),
        ('devolucion', 'Devolución'),
        ('conteo', 'Conteo físico'),
    ]

    id_movimiento = models.AutoField(primary_key=True)
    id_lote = models.ForeignKey(Lote, on_delete=models.CASCADE, db_column='id_lote')
    id_medicamento = models.ForeignKey(Medicamento, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_medicamento')
    id_usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, db_column='id_usuario')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES)
    cantidad = models.IntegerField()
    stock_antes = models.IntegerField()
    stock_despues = models.IntegerField()
    referencia = models.CharField(max_length=120, blank=True)
    notas = models.TextField(blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'movimiento_inventario'
        ordering = ['-fecha', '-id_movimiento']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.cantidad} - {self.id_lote}'

    @property
    def cantidad_kardex(self):
        if self.tipo == self.TIPO_OCULTAMIENTO and self.cantidad == 0:
            return -(self.stock_antes or 0)
        return self.cantidad

    @property
    def stock_despues_kardex(self):
        if self.tipo == self.TIPO_OCULTAMIENTO:
            return 0
        return self.stock_despues


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


class NotificacionCaducidadDescartada(models.Model):
    id_notificacion = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        db_column='id_usuario',
    )
    id_lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        db_column='id_lote',
    )
    fecha_descartada = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notificacion_caducidad_descartada'
        unique_together = ('id_usuario', 'id_lote')

    def __str__(self):
        return f'{self.id_usuario_id} - {self.id_lote_id}'


class ConfiguracionInventario(models.Model):
    id_configuracion = models.AutoField(primary_key=True)
    dias_revision_caducidad = models.PositiveSmallIntegerField(default=1)
    hora_retiro_caducidad = models.TimeField(default=timezone.datetime.strptime('07:10', '%H:%M').time())
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_inventario'
        verbose_name = 'Configuración de inventario'
        verbose_name_plural = 'Configuraciones de inventario'

    def __str__(self):
        return f'Caducidad: {self.dias_revision_caducidad} día(s), {self.hora_retiro_caducidad}'

    @classmethod
    def obtener(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion
