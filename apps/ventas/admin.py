from django.contrib import admin # pyright: ignore[reportMissingModuleSource]
from django.db.models import Sum
from django.utils.html import format_html

from .models import MetodoPago, Venta, DetalleVenta


# ─────────────────────────────────────────────────────
# Método de pago
# ─────────────────────────────────────────────────────
@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display  = ['id_metPag', 'nombre_metodo', 'descripcion', 'num_ventas']
    search_fields = ['nombre_metodo']
    ordering      = ['nombre_metodo']

    @admin.display(description='# Ventas')
    def num_ventas(self, obj):
        return obj.venta_set.count()


# ─────────────────────────────────────────────────────
# Inline: líneas de productos dentro de una venta
# ─────────────────────────────────────────────────────
class DetalleVentaInline(admin.TabularInline):
    model           = DetalleVenta
    extra           = 1           # líneas vacías extras para agregar
    min_num         = 1
    fields          = ['id_medicamento', 'cantidad', 'precio_unitario', 'subtotal']
    readonly_fields = ['subtotal']

    def get_readonly_fields(self, request, obj=None):
        # Si la venta ya existe (edición), bloquear todos los campos
        if obj:
            return ['id_medicamento', 'cantidad', 'precio_unitario', 'subtotal']
        return ['subtotal']


# ─────────────────────────────────────────────────────
# Venta
# ─────────────────────────────────────────────────────
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    # ── Listado ──────────────────────────────────────
    list_display  = [
        'id_ventas', 'fecha_venta', 'id_usuario',
        'cliente_display', 'id_metPag',
        'total_formateado', 'num_productos',
    ]
    list_filter   = ['id_metPag', 'id_usuario', 'fecha_venta']
    search_fields = [
        'id_usuario__nombre', 'id_cliente__nombre',
        'id_cliente__ap_pat',
    ]
    date_hierarchy = 'fecha_venta'
    ordering       = ['-fecha_venta']
    list_per_page  = 30

    # ── Formulario ────────────────────────────────────
    fieldsets = (
        ('Datos de la venta', {
            'fields': ('id_usuario', 'id_metPag', 'id_cliente', 'fecha_venta')
        }),
        ('Totales', {
            'fields': ('total_venta',)
        }),
    )
    readonly_fields = ['total_venta']
    inlines         = [DetalleVentaInline]

    # ── Columnas calculadas ───────────────────────────
    @admin.display(description='Cliente')
    def cliente_display(self, obj):
        return obj.cliente_display()

    @admin.display(description='Total')
    def total_formateado(self, obj):
        if obj.total_venta is not None:
            return format_html(
                '<strong style="color:#1a6b3c;">${}</strong>',
                f'{obj.total_venta:,.2f}'
            )
        return '—'

    @admin.display(description='Productos')
    def num_productos(self, obj):
        return obj.num_productos()

    # ── Evitar eliminar ventas desde el admin ─────────
    def has_delete_permission(self, request, obj=None):
        # Solo superusuarios pueden cancelar ventas
        return request.user.is_superuser


# ─────────────────────────────────────────────────────
# Detalle de venta (vista de solo lectura)
# ─────────────────────────────────────────────────────
@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display  = [
        'id_detalle', 'id_ventas', 'id_medicamento',
        'cantidad', 'precio_unitario', 'subtotal',
    ]
    list_filter   = ['id_ventas__id_metPag']
    search_fields = ['id_medicamento__nombre', 'id_ventas__id_ventas']
    ordering      = ['-id_ventas']
    list_per_page = 50

    # Los detalles no deben modificarse manualmente
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser