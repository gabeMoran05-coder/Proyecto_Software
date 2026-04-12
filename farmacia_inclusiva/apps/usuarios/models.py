from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UsuarioManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('cajero', 'Cajero'),
    ]

    username   = models.CharField('Usuario', max_length=150, unique=True)
    nombre     = models.CharField('Nombre', max_length=100)
    ap_pat     = models.CharField('Apellido paterno', max_length=100)
    ap_mat     = models.CharField('Apellido materno', max_length=100, blank=True)
    telefono   = models.CharField('Teléfono', max_length=20, blank=True)
    rol        = models.CharField('Rol', max_length=10, choices=ROL_CHOICES, default='cajero')
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    fecha_creacion   = models.DateTimeField('Fecha de creación', auto_now_add=True)
    ultima_conexion  = models.DateTimeField('Última conexión', null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nombre', 'ap_pat']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} {self.ap_pat} ({self.get_rol_display()})"

    def nombre_completo(self):
        return f"{self.nombre} {self.ap_pat} {self.ap_mat}".strip()
