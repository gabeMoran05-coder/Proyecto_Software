from django.contrib import admin
from django.utils.html import format_html

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # ── Listado ──────────────────────────────────────────────────
    list_display  = [
        'id_usuario', 'usuario', 'nombre_completo_display',
        'rol_badge', 'estado_badge', 'puesto', 'telefono', 'fecha_contratacion', 'fecha_baja',
        'ultima_conexion', 'num_ventas',
    ]
    list_filter   = ['rol', 'activo', 'fecha_contratacion', 'fecha_baja']
    search_fields = ['usuario', 'nombre', 'ap_pat', 'ap_mat', 'puesto']
    ordering      = ['nombre', 'ap_pat']
    list_per_page = 25

    # ── Formulario ───────────────────────────────────────────────
    fieldsets = (
        ('Cuenta', {
            'fields': ('usuario', 'rol')
        }),
        ('Datos personales', {
            'fields': ('nombre', 'ap_pat', 'ap_mat', 'telefono')
        }),
        ('Datos laborales', {
            'fields': ('puesto', 'activo', 'fecha_contratacion', 'fecha_baja')
        }),
        ('Actividad', {
            'fields': ('fecha_creacion', 'ultima_conexion'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['ultima_conexion']

    # ── Columnas calculadas ───────────────────────────────────────
    @admin.display(description='Nombre completo')
    def nombre_completo_display(self, obj):
        return obj.nombre_completo()

    @admin.display(description='Rol')
    def rol_badge(self, obj):
        colores = {
            'admin':   '#1565c0',
            'cajero':  '#1b5e20',
            'almacen': '#8a5e0a',
        }
        fondos = {
            'admin':   '#e3f0ff',
            'cajero':  '#e8f5e9',
            'almacen': '#fff3cd',
        }
        color = colores.get(obj.rol, '#546e7a')
        fondo = fondos.get(obj.rol, '#eceff1')
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:12px;'
            'font-size:0.8rem;font-weight:600;">{}</span>',
            fondo, color, obj.get_rol_display()
        )

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        if obj.activo:
            return format_html(
                '<span style="background:#e8f5e9;color:#1b5e20;padding:2px 8px;'
                'border-radius:12px;font-size:0.8rem;font-weight:600;">Activo</span>'
            )
        return format_html(
            '<span style="background:#eceff1;color:#546e7a;padding:2px 8px;'
            'border-radius:12px;font-size:0.8rem;font-weight:600;">Inactivo</span>'
        )

    @admin.display(description='# Ventas')
    def num_ventas(self, obj):
        return obj.total_ventas_registradas()
