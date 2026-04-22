from django.db import models
from django.contrib.auth.hashers import check_password, make_password


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
        max_length=15, null=True, blank=True, verbose_name='Telefono'
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
        max_length=128, blank=True, verbose_name='Contrasena'
    )

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nombre', 'ap_pat']

    def __str__(self):
        return f'{self.nombre_completo()} (@{self.usuario})'

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
