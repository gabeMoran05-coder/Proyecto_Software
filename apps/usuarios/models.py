from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.text_utils import first_upper, first_upper_or_none


class Usuario(models.Model):
    ROL_ADMIN = 'admin'
    ROL_ADMINISTRADOR = 'administrador'
    ROL_CAJERO = 'cajero'
    ROL_ALMACEN = 'almacen'
    ROL_FARMACEUTICO = 'farmaceutico'

    ROL_CHOICES = [
        (ROL_ADMIN, 'Administrador'),
        (ROL_ADMINISTRADOR, 'Administrador'),
        (ROL_CAJERO, 'Cajero'),
        (ROL_ALMACEN, 'Almacen'),
        (ROL_FARMACEUTICO, 'Farmaceutico'),
    ]
    ROL_PUBLIC_CHOICES = [
        (ROL_ADMIN, 'Administrador'),
        (ROL_CAJERO, 'Cajero'),
        (ROL_ALMACEN, 'Almacen'),
        (ROL_FARMACEUTICO, 'Farmaceutico'),
    ]

    id_usuario = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=60, unique=True, verbose_name='Usuario')
    rol = models.CharField(max_length=30, choices=ROL_CHOICES, verbose_name='Rol')
    fecha_creacion = models.DateField(
        null=True, blank=True, verbose_name='Fecha de creacion'
    )
    ultima_conexion = models.DateTimeField(
        null=True, blank=True, verbose_name='Ultima conexion'
    )
    nombre = models.CharField(max_length=80, verbose_name='Nombre(s)')
    ap_pat = models.CharField(
        max_length=60, null=True, blank=True, verbose_name='Apellido paterno'
    )
    ap_mat = models.CharField(
        max_length=60, null=True, blank=True, verbose_name='Apellido materno'
    )
    telefono = models.CharField(
        max_length=15, null=True, blank=True, verbose_name='Teléfono'
    )
    email = models.EmailField(
        max_length=254, null=True, blank=True, verbose_name='Correo electronico'
    )
    puesto = models.CharField(
        max_length=80, null=True, blank=True, verbose_name='Puesto'
    )
    fecha_contratacion = models.DateField(
        null=True, blank=True, verbose_name='Fecha de contratacion'
    )
    fecha_baja = models.DateField(
        null=True, blank=True, verbose_name='Ultimo dia'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    password_hash = models.CharField(
        max_length=128, blank=True, verbose_name='Contraseña'
    )

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nombre', 'ap_pat']

    def __str__(self):
        return f'{self.nombre_completo()} (@{self.usuario})'

    def save(self, *args, **kwargs):
        self.nombre = first_upper(self.nombre)
        self.ap_pat = first_upper_or_none(self.ap_pat)
        self.ap_mat = first_upper_or_none(self.ap_mat)
        self.puesto = first_upper_or_none(self.puesto)
        if not self.fecha_creacion:
            self.fecha_creacion = timezone.localdate()
        super().save(*args, **kwargs)

    @property
    def username(self):
        return self.usuario

    @username.setter
    def username(self, value):
        self.usuario = value

    @property
    def first_name(self):
        return self.nombre

    @first_name.setter
    def first_name(self, value):
        self.nombre = value

    @property
    def last_name(self):
        return ' '.join(part for part in [self.ap_pat, self.ap_mat] if part)

    @last_name.setter
    def last_name(self, value):
        parts = (value or '').split(' ', 1)
        self.ap_pat = parts[0] if parts else None
        self.ap_mat = parts[1] if len(parts) > 1 else None

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    def rol_normalizado(self):
        if self.rol == self.ROL_ADMINISTRADOR:
            return self.ROL_ADMIN
        return self.rol

    def es_admin(self):
        return self.rol_normalizado() == self.ROL_ADMIN

    def get_full_name(self):
        return self.nombre_completo()

    def nombre_completo(self):
        partes = [self.nombre, self.ap_pat, self.ap_mat]
        return ' '.join(part for part in partes if part)

    def estado_laboral_display(self):
        return 'Activo' if self.activo else 'Inactivo'

    def total_ventas_registradas(self):
        return self.venta_set.count()


class NotificacionSistema(models.Model):
    NIVEL_INFO = 'info'
    NIVEL_SUCCESS = 'success'
    NIVEL_WARNING = 'warning'
    NIVEL_DANGER = 'danger'

    NIVEL_CHOICES = [
        (NIVEL_INFO, 'Informacion'),
        (NIVEL_SUCCESS, 'Correcto'),
        (NIVEL_WARNING, 'Advertencia'),
        (NIVEL_DANGER, 'Critico'),
    ]

    id_notificacion = models.AutoField(primary_key=True)
    clave = models.CharField(max_length=120, unique=True)
    titulo = models.CharField(max_length=120)
    mensaje = models.CharField(max_length=255)
    categoria = models.CharField(max_length=60, blank=True)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default=NIVEL_INFO)
    url = models.CharField(max_length=255, blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notificacion_sistema'
        ordering = ['-fecha_actualizacion', '-fecha_creacion']
        verbose_name = 'Notificacion del sistema'
        verbose_name_plural = 'Notificaciones del sistema'

    def __str__(self):
        return self.titulo


class NotificacionSistemaDescartada(models.Model):
    id_descartada = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='id_usuario',
    )
    id_notificacion = models.ForeignKey(
        NotificacionSistema,
        on_delete=models.CASCADE,
        db_column='id_notificacion',
    )
    fecha_descartada = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notificacion_sistema_descartada'
        unique_together = ('id_usuario', 'id_notificacion')
        verbose_name = 'Notificacion descartada'
        verbose_name_plural = 'Notificaciones descartadas'

    def __str__(self):
        return f'{self.id_usuario} - {self.id_notificacion}'
