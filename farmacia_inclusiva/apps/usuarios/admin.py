from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'nombre', 'ap_pat', 'rol', 'is_active', 'ultima_conexion']
    list_filter  = ['rol', 'is_active']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Datos personales', {'fields': ('nombre', 'ap_pat', 'ap_mat', 'telefono')}),
        ('Permisos', {'fields': ('rol', 'is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2', 'nombre', 'ap_pat', 'rol')}),
    )
    search_fields = ['username', 'nombre', 'ap_pat']
    ordering = ['nombre']
