from django.contrib import admin
from .models import Venta, DetalleVenta, MetodoPago, Cliente

class DetalleInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ['subtotal']

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'usuario', 'cliente', 'metodo_pago', 'total_venta', 'fecha_venta']
    list_filter   = ['metodo_pago', 'fecha_venta']
    inlines       = [DetalleInline]

@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'ap_pat', 'telefono', 'fecha_registro']
    search_fields = ['nombre', 'ap_pat', 'telefono']
