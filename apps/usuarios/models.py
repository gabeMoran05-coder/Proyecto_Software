from django.db import models
from datetime import time

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
        (ROL_ALMACEN, 'Almacén'),
    ]

    id_usuario = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=60, unique=True, verbose_name='Usuario')
    rol = models.CharField(max_length=30, choices=ROL_CHOICES, verbose_name='Rol')
    fecha_creacion = models.DateField(
        null=True, blank=True, verbose_name='Fecha de creacion'
    )
    ultima_conexion = models.DateTimeField(
        null=True, blank=True, verbose_name='Última conexión'
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
        null=True, blank=True, verbose_name='Último día'
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
        (NIVEL_INFO, 'Información'),
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
        verbose_name = 'Notificación del sistema'
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
        verbose_name = 'Notificación descartada'
        verbose_name_plural = 'Notificaciones descartadas'

    def __str__(self):
        return f'{self.id_usuario} - {self.id_notificacion}'


class AuditoriaEvento(models.Model):
    NIVEL_INFO = 'info'
    NIVEL_WARNING = 'warning'
    NIVEL_DANGER = 'danger'

    NIVEL_CHOICES = [
        (NIVEL_INFO, 'Información'),
        (NIVEL_WARNING, 'Advertencia'),
        (NIVEL_DANGER, 'Critico'),
    ]

    id_evento = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_usuario',
    )
    accion = models.CharField(max_length=80)
    modulo = models.CharField(max_length=60)
    objeto_tipo = models.CharField(max_length=80, blank=True)
    objeto_id = models.CharField(max_length=80, blank=True)
    descripcion = models.TextField(blank=True)
    motivo = models.CharField(max_length=160, blank=True)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default=NIVEL_INFO)
    url = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'auditoria_evento'
        ordering = ['-fecha', '-id_evento']
        verbose_name = 'Evento de auditoria'
        verbose_name_plural = 'Eventos de auditoria'

    def __str__(self):
        return f'{self.modulo} - {self.accion}'


class AutomatizacionCorreo(models.Model):
    TAREA_RESUMEN_DIARIO = 'resumen_diario'
    TAREA_REPORTE_SEMANAL = 'reporte_semanal'
    TAREA_REPORTE_MENSUAL = 'reporte_mensual'
    SECCION_GENERAL = 'general'
    SECCION_VENTAS = 'ventas'
    SECCION_CLIENTES = 'clientes'
    SECCION_MEDICAMENTOS = 'medicamentos'
    SECCION_INVENTARIO = 'inventario'

    TAREA_CHOICES = [
        (TAREA_RESUMEN_DIARIO, 'Resumen diario de ventas'),
        (TAREA_REPORTE_SEMANAL, 'Reporte semanal'),
        (TAREA_REPORTE_MENSUAL, 'Reporte mensual'),
    ]
    DIA_SEMANA_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miercoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sabado'),
        (6, 'Domingo'),
    ]
    SECCION_CHOICES = [
        (SECCION_GENERAL, 'Reporte general'),
        (SECCION_VENTAS, 'Ventas'),
        (SECCION_CLIENTES, 'Clientes'),
        (SECCION_MEDICAMENTOS, 'Medicamentos'),
        (SECCION_INVENTARIO, 'Inventario y caducidad'),
    ]
    DEFAULTS = [
        {
            'clave': 'ventas.resumen_diario',
            'nombre': 'Resumen diario de ventas',
            'descripcion': 'Envía por correo el resumen de ventas del día.',
            'tarea': TAREA_RESUMEN_DIARIO,
            'seccion_reporte': SECCION_VENTAS,
            'hora_envio': time(21, 0),
            'dia_semana': 0,
            'dia_mes': 1,
        },
        {
            'clave': 'reportes.reporte_semanal',
            'nombre': 'Reporte semanal',
            'descripcion': 'Envía PDF y Excel con el reporte de la semana anterior.',
            'tarea': TAREA_REPORTE_SEMANAL,
            'seccion_reporte': SECCION_GENERAL,
            'hora_envio': time(8, 0),
            'dia_semana': 0,
            'dia_mes': 1,
        },
        {
            'clave': 'reportes.reporte_mensual',
            'nombre': 'Reporte mensual',
            'descripcion': 'Envía PDF y Excel con el reporte del mes anterior.',
            'tarea': TAREA_REPORTE_MENSUAL,
            'seccion_reporte': SECCION_GENERAL,
            'hora_envio': time(8, 15),
            'dia_semana': 0,
            'dia_mes': 1,
        },
    ]
    for seccion, etiqueta in SECCION_CHOICES[1:]:
        DEFAULTS.extend([
            {
                'clave': f'reportes.{seccion}.semanal',
                'nombre': f'{etiqueta} semanal',
                'descripcion': f'Envía PDF y Excel solo de {etiqueta.lower()} de la semana anterior.',
                'tarea': TAREA_REPORTE_SEMANAL,
                'seccion_reporte': seccion,
                'activa': False,
                'hora_envio': time(8, 0),
                'dia_semana': 0,
                'dia_mes': 1,
            },
            {
                'clave': f'reportes.{seccion}.mensual',
                'nombre': f'{etiqueta} mensual',
                'descripcion': f'Envía PDF y Excel solo de {etiqueta.lower()} del mes anterior.',
                'tarea': TAREA_REPORTE_MENSUAL,
                'seccion_reporte': seccion,
                'activa': False,
                'hora_envio': time(8, 15),
                'dia_semana': 0,
                'dia_mes': 1,
            },
        ])

    id_automatizacion = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='id_usuario',
    )
    clave = models.CharField(max_length=120)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True)
    tarea = models.CharField(max_length=40, choices=TAREA_CHOICES)
    seccion_reporte = models.CharField(max_length=30, choices=SECCION_CHOICES, default=SECCION_GENERAL)
    activa = models.BooleanField(default=True)
    hora_envio = models.TimeField(default=time(8, 0))
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_SEMANA_CHOICES, default=0)
    dia_mes = models.PositiveSmallIntegerField(default=1)
    ultimo_envio = models.DateField(null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'automatizacion_correo'
        ordering = ['id_automatizacion']
        unique_together = ('id_usuario', 'clave')
        verbose_name = 'Automatizacion de correo'
        verbose_name_plural = 'Automatizaciones de correo'

    def __str__(self):
        return self.nombre

    @classmethod
    def ensure_defaults(cls, usuario=None):
        automatizaciones = []
        for data in cls.DEFAULTS:
            defaults = data.copy()
            clave = defaults.pop('clave')
            defaults['id_usuario'] = usuario
            automatizacion, _ = cls.objects.get_or_create(
                id_usuario=usuario,
                clave=clave,
                defaults=defaults,
            )
            automatizaciones.append(automatizacion)
        return automatizaciones

    def destinatario_email(self):
        if self.id_usuario and self.id_usuario.activo and self.id_usuario.email:
            return self.id_usuario.email
        return ''

    def frecuencia_display(self):
        if self.tarea == self.TAREA_RESUMEN_DIARIO:
            return 'Diario'
        if self.tarea == self.TAREA_REPORTE_SEMANAL:
            return f'Cada {self.get_dia_semana_display()}'
            return f'Día {self.dia_mes} de cada mes'

    @property
    def seccion_pdf(self):
        return None if self.seccion_reporte == self.SECCION_GENERAL else self.seccion_reporte

    @property
    def tab_key(self):
        if self.tarea == self.TAREA_RESUMEN_DIARIO:
            return 'resumen'
        return self.seccion_reporte
