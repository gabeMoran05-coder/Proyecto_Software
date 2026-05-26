from django.contrib import admin
from django.db.models import Sum

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    # ── Listado ──────────────────────────────────────────────────
    list_display  = [
        'id_cliente', 'nombre_completo', 'ap_pat', 'ap_mat',
        'telefono', 'fecha_registro', 'num_compras',
    ]
    search_fields = ['nombre', 'ap_pat', 'ap_mat', 'telefono']
    list_filter   = ['fecha_registro']
    ordering      = ['nombre', 'ap_pat']
    list_per_page = 25

    # ── Formulario ───────────────────────────────────────────────
    fieldsets = (
        ('Datos personales', {
            'fields': ('nombre', 'ap_pat', 'ap_mat')
        }),
        ('Contacto y registro', {
            'fields': ('telefono', 'fecha_registro')
        }),
    )

    # ── Columnas calculadas ───────────────────────────────────────
    @admin.display(description='Nombre completo')
    def nombre_completo(self, obj):
        return str(obj)

    @admin.display(description='# Compras')
    def num_compras(self, obj):
        return obj.venta_set.count()