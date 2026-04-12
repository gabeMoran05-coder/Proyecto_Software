from django.db import models
from django.utils import timezone
import qrcode
import io
import uuid
from django.core.files import File


class Medicamento(models.Model):
    COLORIMETRIA_CHOICES = [
        ('verde',    'Vigente'),
        ('amarillo', 'Próximo a caducar'),
        ('rojo',     'Caducado'),
    ]
    nombre              = models.CharField('Nombre comercial', max_length=200)
    presentacion        = models.CharField('Presentación', max_length=100)
    concentracion       = models.CharField('Concentración', max_length=100)
    requiere_receta     = models.BooleanField('¿Requiere receta?', default=False)
    estado_colorimetria = models.CharField(
        'Estado', max_length=10, choices=COLORIMETRIA_CHOICES, default='verde'
    )
    fecha_registro = models.DateTimeField('Fecha de registro', auto_now_add=True)

    class Meta:
        verbose_name = 'Medicamento'
        verbose_name_plural = 'Medicamentos'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} {self.concentracion} ({self.presentacion})"

    def actualizar_colorimetria(self):
        lotes = self.lotes.filter(activo=True).order_by('fecha_caducidad')
        if not lotes.exists():
            self.estado_colorimetria = 'rojo'
        else:
            hoy   = timezone.now().date()
            dias  = (lotes.first().fecha_caducidad - hoy).days
            if dias < 0:
                self.estado_colorimetria = 'rojo'
            elif dias <= 30:
                self.estado_colorimetria = 'amarillo'
            else:
                self.estado_colorimetria = 'verde'
        self.save(update_fields=['estado_colorimetria'])


class Lote(models.Model):
    medicamento       = models.ForeignKey(Medicamento, on_delete=models.CASCADE, related_name='lotes')
    # FK a Proveedor via string para evitar import circular
    proveedor         = models.ForeignKey(
        'proveedores.Proveedor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='lotes'
    )
    numero_lote       = models.CharField('Número de lote', max_length=100)
    fecha_fabricacion = models.DateField('Fecha de fabricación')
    fecha_caducidad   = models.DateField('Fecha de caducidad')
    fecha_ingreso     = models.DateField('Fecha de ingreso', auto_now_add=True)
    stock_actual      = models.PositiveIntegerField('Stock actual', default=0)
    activo            = models.BooleanField('Activo', default=True)
    precio_compra     = models.DecimalField('Precio de compra', max_digits=10, decimal_places=2)
    precio_venta      = models.DecimalField('Precio de venta',  max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['fecha_caducidad']
        unique_together = [['medicamento', 'numero_lote']]

    def __str__(self):
        return f"Lote {self.numero_lote} – {self.medicamento.nombre}"

    @property
    def dias_para_caducar(self):
        return (self.fecha_caducidad - timezone.now().date()).days

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.medicamento.actualizar_colorimetria()


class CodigoQR(models.Model):
    medicamento        = models.OneToOneField(Medicamento, on_delete=models.CASCADE, related_name='codigo_qr')
    token              = models.UUIDField('Token', default=uuid.uuid4, unique=True)
    url_qr             = models.URLField('URL de consulta', max_length=500, blank=True)
    imagen_qr          = models.ImageField('Imagen QR', upload_to='qr/', blank=True)
    fecha_generacion   = models.DateTimeField('Fecha de generación', auto_now_add=True)
    fecha_regeneracion = models.DateTimeField('Fecha de regeneración', null=True, blank=True)
    contador_escaneos  = models.PositiveIntegerField('Escaneos', default=0)
    activo             = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Código QR'
        verbose_name_plural = 'Códigos QR'

    def __str__(self):
        return f"QR – {self.medicamento.nombre}"

    def generar_imagen(self, base_url):
        self.url_qr = f"{base_url}/medicamentos/qr/{self.token}/"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(self.url_qr)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        self.imagen_qr.save(f"qr_{self.medicamento.id}.png", File(buf), save=False)
        self.save()
