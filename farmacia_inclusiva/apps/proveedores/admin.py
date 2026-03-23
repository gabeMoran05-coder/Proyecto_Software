from django.contrib import admin
from .models import Proveedor

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'telefono', 'correo']
    search_fields = ['nombre']
