from django.contrib import admin
from .models import Medicamento, Lote, CodigoQR

@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'presentacion', 'concentracion', 'estado_colorimetria', 'requiere_receta']
    list_filter   = ['estado_colorimetria', 'requiere_receta']
    search_fields = ['nombre']

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display  = ['numero_lote', 'medicamento', 'stock_actual', 'fecha_caducidad', 'activo']
    list_filter   = ['activo']
    search_fields = ['numero_lote', 'medicamento__nombre']

@admin.register(CodigoQR)
class CodigoQRAdmin(admin.ModelAdmin):
    list_display    = ['medicamento', 'token', 'contador_escaneos', 'activo']
    readonly_fields = ['token', 'contador_escaneos', 'fecha_generacion']
